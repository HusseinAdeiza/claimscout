#!/usr/bin/env python3
"""
ClaimScout demo video generator.

Renders a self-playing ~85s hackathon demo from real ClaimScout output. No screen
recording needed: every frame is drawn programmatically (Pillow) and assembled with
ffmpeg. Beats follow the 6-beat persona arc.

The demo content is REAL — the scan output and the ranking are captured from actual
ClaimScout runs, not mocked, so the numbers on screen are genuine.

Usage:
    python3 make_demo.py [--out demo.mp4] [--width 1280] [--height 720] [--fps 30]

Requires: Pillow, ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- fonts
FONT_PATHS = {
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "mono_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "sans_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _font_cache:
        path = FONT_PATHS.get(kind, FONT_PATHS["mono"])
        if not os.path.exists(path):
            path = FONT_PATHS["mono"]
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ---------------------------------------------------------------- palette (dark terminal theme)
BG = (13, 17, 23)
BG_SOFT = (22, 27, 34)
FG = (230, 237, 243)
DIM = (139, 148, 158)
GREEN = (63, 185, 80)
CYAN = (88, 166, 255)
YELLOW = (210, 168, 255)
ORANGE = (255, 166, 87)
RED = (248, 81, 73)
PURPLE = (188, 140, 255)
WHITE = (255, 255, 255)


# ---------------------------------------------------------------- helpers
def text_w(draw: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(s, font=f)


def draw_text(draw, xy, s, f, fill, anchor=None):
    draw.text(xy, s, font=f, fill=fill, anchor=anchor)


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- real demo data
# Captured from actual `claimscout` runs (see docs/demo-ranking.txt).
SCAN_LINES = [
    ("head", "0dotxyz/marginfi-v2: 10 claimable"),
    ("row", "#705", "unclaimed, 0 comment(s), created 2026-10-12", "Same-asset-emode weight inversion", "bug", CYAN),
    ("row", "#682", "unclaimed, 0 comment(s), created 2026-09-18", "Allow empty-but-active integration balances to close", "bug, good first issue", GREEN),
    ("row", "#701", "unclaimed, 0 comment(s), created 2026-10-10", "Liquidation interplay with Order tagging", "bug, low priority", ORANGE),
]

RANK_LINES = [
    ("1.", "#682", "90", "Bounded bug with clear reproduction, matches contributor's skills", GREEN),
    ("2.", "#705", "80", "Bounded bug, matches contributor's skills", CYAN),
    ("3.", "#701", "70", "Bounded bug, matches skills, labeled good first issue", ORANGE),
]


# ---------------------------------------------------------------- frame primitives
def new_frame(w, h, color=BG):
    img = Image.new("RGB", (w, h), color)
    return img, ImageDraw.Draw(img)


def terminal_chrome(img, draw, w, h, title="claimscout — zsh"):
    """Draw a window with a title bar and three traffic-light dots."""
    bar = 40
    draw.rectangle([0, 0, w, bar], fill=BG_SOFT)
    for i, c in enumerate((RED, YELLOW, GREEN)):
        cx = 24 + i * 26
        draw.ellipse([cx - 7, bar // 2 - 7, cx + 7, bar // 2 + 7], fill=c)
    draw_text(draw, (w // 2, bar // 2), title, font("sans", 16), DIM, anchor="mm")
    return bar


def caption_bar(draw, w, h, text, color=CYAN):
    """Bottom caption with a colored accent bar."""
    y = h - 64
    draw.rectangle([0, y, w, h], fill=BG_SOFT)
    draw.rectangle([0, y, 8, h], fill=color)
    draw_text(draw, (28, y + 32), text, font("sans_bold", 24), FG, anchor="lm")


# ================================================================ BEAT 1: friction
def beat1(w, h, fps):
    """Persona + high-stakes friction: a wall of dead-end issues."""
    dur = 15
    n = dur * fps
    dead = [
        ("#1042", "assigned to @someone", RED),
        ("#1088", "23 comments — contested", ORANGE),
        ("#1101", "epic · no owner · 4 months old", PURPLE),
    ]
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        bar = terminal_chrome(img, draw, w, h, "github.com — issues")

        # scrolling issue list (moves upward over time)
        y = 70
        scroll = int(t * 120)
        for i in range(12):
            num = 1000 + i * 7
            yy = y + i * 52 - scroll
            if yy < bar + 10 or yy > h - 120:
                continue
            col = DIM if i % 2 else FG
            draw_text(draw, (40, yy), f"#{num}", font("mono", 22), col)
            draw_text(draw, (150, yy), "open issue title lorem ipsum dolor", font("mono", 20), DIM)

        # the dead-end callouts slam in during 0:06-0:12 (t 0.4-0.8)
        for j, (num, why, col) in enumerate(dead):
            local = clamp((t - 0.4 - j * 0.13) / 0.12, 0, 1)
            if local <= 0:
                continue
            e = ease_out_cubic(local)
            bx, by = 120, 300 + j * 96
            # slide in from left
            x = int(lerp(-360, bx, e))
            draw.rounded_rectangle([x, by, x + 640, by + 76], radius=12,
                                   fill=BG_SOFT, outline=col, width=3)
            draw_text(draw, (x + 20, by + 24), num, font("mono_bold", 24), col)
            draw_text(draw, (x + 130, by + 27), why, font("mono", 20), FG)

        # final text slam "Sound familiar?" at the very end
        slam = clamp((t - 0.86) / 0.1, 0, 1)
        if slam > 0:
            e = ease_out_cubic(slam)
            size = int(lerp(70, 58, e))
            draw_text(draw, (w // 2, h // 2), "Sound familiar?",
                      font("sans_bold", size), WHITE, anchor="mm")
        yield img


# ================================================================ BEAT 2: reveal
def beat2(w, h, fps):
    """Clean terminal, logo types on, one command types out."""
    dur = 10
    n = dur * fps
    logo = "ClaimScout"
    cmd = "claimscout scan --repos 0dotxyz/marginfi-v2"
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        bar = terminal_chrome(img, draw, w, h)
        # logo types in 0-0.4
        shown = logo[: int(len(logo) * clamp(t / 0.4, 0, 1))]
        lf = font("sans_bold", 54)
        lw = text_w(draw, logo, lf)
        draw_text(draw, (w // 2 - lw / 2, 200), shown, lf, GREEN)
        # blinking cursor after logo
        if t > 0.4 and int(t * 2) % 2 == 0:
            draw.rectangle([w // 2 + lw / 2 + 4, 168, w // 2 + lw / 2 + 18, 218], fill=GREEN)
        # command types in 0.45-0.8
        if t > 0.45:
            cs = cmd[: int(len(cmd) * clamp((t - 0.45) / 0.35, 0, 1))]
            draw_text(draw, (60, 340), "$ " + cs, font("mono", 26), FG)
        # tagline overlay at end
        if t > 0.82:
            draw_text(draw, (w // 2, 470), "Only the issues worth your time.",
                      font("sans", 26), CYAN, anchor="mm")
        yield img


# ================================================================ BEAT 3: live demo + aha
def beat3(w, h, fps):
    """Real scan output streams in; callouts; then the ranker and the aha."""
    dur = 25
    n = dur * fps
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        bar = terminal_chrome(img, draw, w, h, "claimscout scan")

        # --- scan output streams in during t 0 - 0.5
        y = 70
        for i, line in enumerate(SCAN_LINES):
            appear = clamp((t - i * 0.06) / 0.05, 0, 1)
            if appear <= 0:
                continue
            if line[0] == "head":
                draw_text(draw, (40, y), line[1], font("mono_bold", 22), FG)
            else:
                _, num, meta, title, labels, col = line
                draw_text(draw, (40, y), num, font("mono_bold", 22), col)
                draw_text(draw, (140, y), meta, font("mono", 18), DIM)
                draw_text(draw, (40, y + 26), title, font("mono", 20), FG)
                draw_text(draw, (40, y + 50), f"labels: {labels}", font("mono", 16), col)
            y += 92

        # --- callout 1 on #705 (t ~0.45), callout 2 on #682 (t ~0.58)
        callouts = [
            (0.45, 150, "#705", "unclaimed · 0 comments · labeled bug", CYAN),
            (0.58, 150, "#682", "bounded · good first issue", GREEN),
        ]
        for start, yy, tag, why, col in callouts:
            local = clamp((t - start) / 0.08, 0, 1)
            if local <= 0:
                continue
            e = ease_out_cubic(local)
            x = int(lerp(w, w - 470, e))
            draw.rounded_rectangle([x, yy, x + 430, yy + 54], radius=10,
                                   fill=(28, 40, 32), outline=col, width=2)
            draw_text(draw, (x + 14, yy + 26), f"{tag}  {why}", font("mono", 16), col, anchor="lm")

        # --- the pipe + ranker appears at t 0.66
        if t > 0.66:
            draw_text(draw, (40, 470), "$ ... --json | claimscout-rank --profile rust,anchor",
                      font("mono", 20), DIM)
            ry = 510
            for i, (rank, num, score, reason, col) in enumerate(RANK_LINES):
                appear = clamp((t - 0.7 - i * 0.07) / 0.05, 0, 1)
                if appear <= 0:
                    continue
                highlight = (i == 0)
                if highlight and t > 0.86:
                    # the aha: #682 pulses to #1
                    pulse = 0.5 + 0.5 * math.sin(t * 10)
                    col = tuple(int(lerp(c, 255, pulse * 0.3)) for c in GREEN)
                draw_text(draw, (40, ry), f"{rank:>3} {num} [{score}]", font("mono_bold", 20), col)
                draw_text(draw, (250, ry), reason[:58], font("mono", 16), DIM)
                ry += 34

        if t > 0.9:
            caption_bar(draw, w, h, "Number one. Hers to take.", GREEN)
        yield img


# ================================================================ BEAT 4: architecture
def beat4(w, h, fps):
    """3-box architecture diagram draws on; two zooms; a caption."""
    dur = 15
    n = dur * fps
    boxes = [
        ("GitHub API", "public issue data", CYAN),
        ("ClaimScout", "deterministic filter\nNO model in the loop", GREEN),
        ("Open-weight model", "meta/llama-3.2\nONE stateless call", PURPLE),
    ]
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h, BG_SOFT)
        draw_text(draw, (w // 2, 60), "Under the hood", font("sans_bold", 30), FG, anchor="mm")

        bw, bh, gap = 300, 150, 80
        total = 3 * bw + 2 * gap
        x0 = (w - total) // 2
        cy = h // 2 - 40
        centers = []
        for i, (title, sub, col) in enumerate(boxes):
            # boxes draw on staggered
            local = clamp((t - i * 0.15) / 0.2, 0, 1)
            if local <= 0:
                centers.append(None)
                continue
            e = ease_out_cubic(local)
            x = x0 + i * (bw + gap)
            hh = int(bh * e)
            yy = cy + (bh - hh) // 2
            draw.rounded_rectangle([x, yy, x + bw, yy + hh], radius=14,
                                   fill=BG, outline=col, width=3)
            if e > 0.6:
                draw_text(draw, (x + bw // 2, yy + hh // 2 - 18), title,
                          font("sans_bold", 24), col, anchor="mm")
                for k, ln in enumerate(sub.split("\n")):
                    draw_text(draw, (x + bw // 2, yy + hh // 2 + 16 + k * 24), ln,
                              font("mono", 15), DIM, anchor="mm")
            centers.append((x + bw // 2, cy + bh // 2))
            # arrow to next box
            if i < 2 and centers[i] and (t > (i + 1) * 0.15):
                ax0 = x + bw + 8
                ax1 = x + bw + gap - 8
                draw.line([ax0, cy + bh // 2, ax1, cy + bh // 2], fill=DIM, width=3)
                draw.polygon([(ax1, cy + bh // 2), (ax1 - 12, cy + bh // 2 - 8),
                              (ax1 - 12, cy + bh // 2 + 8)], fill=DIM)

        # zoom callouts: middle box (t 0.6), right box (t 0.78)
        for start, idx, label in [(0.6, 1, "No tool-loop. No hallucinated calls."),
                                  (0.78, 2, "Cheap enough to actually run.")]:
            local = clamp((t - start) / 0.1, 0, 1)
            if local <= 0 or not centers[idx]:
                continue
            cx, ccy = centers[idx]
            e = ease_out_cubic(local)
            r = int(lerp(0, 150, e))
            draw.ellipse([cx - r, ccy - r, cx + r, ccy + r], outline=YELLOW, width=4)
            draw_text(draw, (w // 2, h - 90), label, font("sans_bold", 24), YELLOW, anchor="mm")
        yield img


# ================================================================ BEAT 5: montage
def beat5(w, h, fps):
    """Three rapid imperative cuts + a three-up."""
    dur = 10
    n = dur * fps
    cards = [
        ("Scan any repo.", "claimscout scan --repos <owner/repo>", CYAN),
        ("Rank on your skills.", "claimscout-rank --profile rust,anchor", GREEN),
        ("Pipe it anywhere.", "claimscout scan --json | jq '.[].number'", PURPLE),
    ]
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h, BG_SOFT)
        # three sequential full-bleed cards in the first 70%
        if t < 0.7:
            idx = min(int(t / 0.233), 2)
            local = (t / 0.233) - idx
            title, cmd, col = cards[idx]
            slide = ease_out_cubic(clamp(local / 0.15, 0, 1))
            x = int(lerp(w, 0, slide))
            draw.rectangle([0, 0, w, h], fill=BG)
            draw.rectangle([0, h // 2 - 90, w, h // 2 + 90], fill=BG_SOFT)
            draw_text(draw, (x + 80, h // 2 - 40), title, font("sans_bold", 52), col)
            draw_text(draw, (x + 80, h // 2 + 30), cmd, font("mono", 24), DIM)
        else:
            # three-up split
            local = clamp((t - 0.7) / 0.15, 0, 1)
            e = ease_out_cubic(local)
            pw = w // 3
            for i, (title, cmd, col) in enumerate(cards):
                x = i * pw
                inset = int(lerp(20, 4, e))
                draw.rectangle([x + inset, inset, x + pw - inset, h - inset],
                               fill=BG, outline=col, width=2)
                draw_text(draw, (x + pw // 2, h // 2 - 20), title,
                          font("sans_bold", 22), col, anchor="mm")
                draw_text(draw, (x + pw // 2, h // 2 + 24), cmd[:22],
                          font("mono", 13), DIM, anchor="mm")
        yield img


# ================================================================ BEAT 6: resolution
def beat6(w, h, fps):
    """Back to the persona, real merged PR, logo + tagline card."""
    dur = 10
    n = dur * fps
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)

        if t < 0.45:
            # a merged PR page (real: genvm-manager #48)
            bar = terminal_chrome(img, draw, w, h, "github.com — pull request")
            draw_text(draw, (40, 70), "fix(manager): report a spawned run as finished",
                      font("sans_bold", 24), FG)
            # the green Merged badge
            bx, by = 40, 120
            draw.rounded_rectangle([bx, by, bx + 150, by + 44], radius=22, fill=PURPLE)
            draw_text(draw, (bx + 75, by + 22), "Merged", font("sans_bold", 22), WHITE, anchor="mm")
            draw_text(draw, (bx + 170, by + 22), "genlayerlabs/genvm-manager #48",
                      font("mono", 18), DIM, anchor="lm")
            draw_text(draw, (40, 200), "+82  −1   2 files   all checks passed",
                      font("mono", 18), GREEN)
            # a subtle confetti burst after the badge lands
            if t > 0.2:
                for i in range(24):
                    ang = i * (math.pi * 2 / 24)
                    dist = 120 + (t - 0.2) * 900
                    cx = bx + 75 + math.cos(ang) * dist
                    cy = by + 22 + math.sin(ang) * dist * 0.7
                    col = [GREEN, CYAN, YELLOW, PURPLE][i % 4]
                    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=col)
        else:
            # logo + tagline card on black
            local = clamp((t - 0.45) / 0.2, 0, 1)
            e = ease_out_cubic(local)
            lf = font("sans_bold", int(lerp(40, 72, e)))
            logo = "ClaimScout"
            lw = text_w(draw, logo, lf)
            draw_text(draw, (w // 2 - lw / 2, h // 2 - 60), logo, lf, GREEN)
            if t > 0.62:
                tl = "Claim what's yours."
                tlw = text_w(draw, tl, font("sans", 30))
                draw_text(draw, (w // 2 - tlw / 2, h // 2 + 30), tl, font("sans", 30), FG)
        yield img


# ================================================================ assemble
def render(out_path, w, h, fps):
    beats = [beat1, beat2, beat3, beat4, beat5, beat6]
    tmp = tempfile.mkdtemp(prefix="claimscout_frames_")
    print(f"rendering frames to {tmp} ...", flush=True)
    idx = 0
    try:
        for bi, beat in enumerate(beats, 1):
            print(f"  beat {bi}/6: {beat.__name__}", flush=True)
            for img in beat(w, h, fps):
                img.save(os.path.join(tmp, f"f{idx:05d}.png"))
                idx += 1
        print(f"  {idx} frames rendered", flush=True)

        cmd = [
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", os.path.join(tmp, "f%05d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", f"scale={w}:{h}", "-movflags", "+faststart",
            out_path,
        ]
        print("  encoding with ffmpeg ...", flush=True)
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"done: {out_path}", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="demo.mp4")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--fps", type=int, default=30)
    a = p.parse_args()
    render(a.out, a.width, a.height, a.fps)


if __name__ == "__main__":
    sys.exit(main())
