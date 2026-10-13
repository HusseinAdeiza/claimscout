#!/usr/bin/env python3
"""
Build the ClaimScout demo audio track and mux it onto the rendered video.

Two inputs:
  1. the per-line voiceover clips from tools/make_voiceover.sh
  2. the silent rendered video (tools/make_demo.py -> demo.mp4)

Each VO clip is placed at a beat-aligned timestamp so the narration lands on the
right visual moment. A subtle music bed is synthesized with ffmpeg (no asset
needed) and ducked under the voice. Output: demo-final.mp4.

Timestamps are in seconds and correspond to the 6-beat script:
  Beat 1  0:00-0:15   Beat 2  0:15-0:25   Beat 3  0:25-0:50
  Beat 4  0:50-1:05   Beat 5  1:05-1:15   Beat 6  1:15-1:25
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

# (clip, start_time) — start times chosen to match the on-screen action.
VO_PLACEMENT = [
    ("vo_01", 0.3),
    ("vo_02", 5.4),
    ("vo_03", 10.0),
    ("vo_04", 12.6),   # lands just before "Sound familiar?" slam
    ("vo_05", 15.2),
    ("vo_06", 25.2),
    ("vo_07", 32.2),   # callout on #705
    ("vo_08", 37.0),   # callout on #682
    ("vo_09", 42.8),
    ("vo_10", 46.6),   # the aha: #682 -> #1
    ("vo_11", 50.2),
    ("vo_12", 57.8),
    ("vo_13", 65.2),
    ("vo_14", 75.2),
    ("vo_15", 78.6),   # merged badge
    ("vo_16", 82.2),   # tagline
]


def dur(path: str) -> float:
    return float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path]
        ).decode().strip()
    )


def build_voiceover(vo_dir: str, out: str, rate: str, length: float) -> str:
    """
    Concatenate the clips at their placed offsets into one narration track.

    Each clip is padded with `apad` to the full video length before mixing, so
    `amix` sees every stream at the same duration and the delays land correctly
    (without the pad, amix truncates to the shortest and the later clips vanish).
    """
    inputs, filters, labels = [], [], []
    for i, (clip, start) in enumerate(VO_PLACEMENT):
        path = os.path.join(vo_dir, f"{clip}.mp3")
        if not os.path.exists(path):
            print(f"  ! missing {path}", file=sys.stderr)
            continue
        inputs += ["-i", path]
        # atempo keeps pitch natural; adelay all=1 works for mono clips;
        # apad forces the stream to the full timeline so amix does not truncate.
        filters.append(
            f"[{i}:a]atempo={rate},"
            f"adelay=delays={int(start*1000)}:all=1,"
            f"apad=whole_dur={length}[v{i}]"
        )
        labels.append(f"[v{i}]")
    mix = ("".join(labels) +
           f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,"
           f"atrim=0:{length},asetpts=N/SR/TB[nar]")
    cmd = (["ffmpeg", "-y"] + inputs +
           ["-filter_complex", ";".join(filters) + ";" + mix,
            "-map", "[nar]", out])
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def synth_music(out: str, seconds: float) -> str:
    """
    Synthesize a simple lo-fi bed: a low pulse that opens up in the middle and
    resolves at the end. Built from sine/triangle oscillators — no asset needed.
    """
    af = (
        # bass pulse ~ every 0.5s
        f"sine=frequency=55:duration={seconds}[bass];"
        # a soft pad chord (A minor-ish) via three sines
        f"sine=frequency=220:duration={seconds}[p1];"
        f"sine=frequency=261.63:duration={seconds}[p2];"
        f"sine=frequency=329.63:duration={seconds}[p3];"
        "[p1][p2][p3]amix=inputs=3:normalize=0[pad];"
        # tremolo the pad so it breathes
        f"[pad]tremolo=f=0.3:d=0.6[pad2];"
        # pulse the bass
        f"[bass]tremolo=f=2:d=0.8[bass2];"
        "[bass2][pad2]amix=inputs=2:weights=0.6 0.4[music];"
        f"[music]volume=0.5,afade=t=in:st=0:d=2,afade=t=out:st={seconds-3}:d=3[m]"
    )
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i",
           f"anullsrc=r=44100:cl=stereo:d={seconds}",
           "-filter_complex", af, "-map", "[m]", out]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def main():
    p = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p.add_argument("--video", default=os.path.join(here, "demo.mp4"))
    p.add_argument("--vo-dir", default=os.path.join(here, "tools", "voiceover_ava"))
    p.add_argument("--out", default=os.path.join(here, "demo-final.mp4"))
    p.add_argument("--rate", default="1.14",
                   help="atempo for narration (>1 = faster); narration is ~4.5s long")
    p.add_argument("--music-vol", default="0.22")
    a = p.parse_args()

    if not os.path.exists(a.video):
        print(f"error: video not found: {a.video}", file=sys.stderr)
        return 1
    length = dur(a.video)
    print(f"video: {a.video} ({length:.1f}s)")

    work = os.path.join(a.vo_dir, "_work")
    os.makedirs(work, exist_ok=True)
    nar = build_voiceover(a.vo_dir, os.path.join(work, "narration.m4a"), a.rate, length)
    print(f"narration built: {dur(nar):.1f}s")
    music = synth_music(os.path.join(work, "music.m4a"), length)
    print(f"music bed built: {dur(music):.1f}s")

    # duck music under voice and mux
    fc = (
        f"[1:a]volume=1.0[n];"
        f"[2:a]volume={a.music_vol}[m];"
        f"[n][m]amix=inputs=2:duration=first:dropout_transition=0[a]"
    )
    cmd = ["ffmpeg", "-y", "-i", a.video, "-i", nar, "-i", music,
           "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", a.out]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"done: {a.out} ({dur(a.out):.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
