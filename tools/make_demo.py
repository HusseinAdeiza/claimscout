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


# ---------------------------------------------------------------- palette
# Style matched to the reference (Elitr / BNB Hack): stark flat BLACK, ONE sparing
# warm-yellow accent, monospace metadata, big bold numerals, generous negative
# space. The polish is restraint + hierarchy, not glow or gradients.
BG = (0, 0, 0)            # true black, as the reference uses
BG_SOFT = (10, 10, 11)    # barely-lifted panel
PANEL = (16, 16, 18)
FG = (245, 245, 245)      # near-white
DIM = (130, 130, 135)     # muted metadata grey
ACCENT = (250, 204, 21)   # the single brand yellow (reference's signature)
GREEN = (74, 222, 128)
CYAN = (96, 165, 250)
ORANGE = (251, 146, 60)
RED = (239, 68, 68)
PURPLE = (167, 139, 250)
YELLOW = ACCENT  # backward-compat alias; the reference has one yellow accent
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


def ease_out_back(t: float) -> float:
    """Springy overshoot — the easing that makes motion feel 'expensive'."""
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# ---------------------------------------------------------------- luxury FX layer
def gradient_backdrop(w, h, t, top=(16, 20, 32), bottom=(8, 10, 18)):
    """A slowly drifting vertical gradient — depth instead of a flat fill.

    Built as a 1-pixel-wide column then resized, which is far faster than a
    per-pixel Python loop over the full frame.
    """
    shift = (math.sin(t * 0.6) + 1) / 2  # 0..1 breathing centre
    col = Image.new("RGB", (1, h))
    cp = col.load()
    for y in range(h):
        f = (y / h + shift * 0.15) % 1.0
        cp[0, y] = (
            int(lerp(top[0], bottom[0], f)),
            int(lerp(top[1], bottom[1], f)),
            int(lerp(top[2], bottom[2], f)),
        )
    return col.resize((w, h))


def add_glow(img, cx, cy, radius, color, strength=90):
    """A soft radial glow composited additively — accent lighting."""
    from PIL import ImageChops
    glow = Image.new("RGB", img.size, (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    steps = 24
    for i in range(steps, 0, -1):
        r = radius * i / steps
        a = int(strength * (1 - i / steps) ** 2)
        c = tuple(min(255, int(ch * a / 255)) for ch in color)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
    return ImageChops.add(img, glow)


def vignette(img, strength=70):
    """Darkened corners — focuses the eye, reads as cinematic."""
    from PIL import ImageFilter
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-w * 0.25, -h * 0.25, w * 1.25, h * 1.25], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    # invert-ish: keep centre, fade edges to black by `strength`
    mask = mask.point(lambda p: int(255 - (255 - p) * strength / 255))
    black = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, black, mask)


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


def ref_chrome(draw, w, h, corner_tl="", corner_tr="", ticker=None):
    """
    Reference-style frame furniture:
      - a thin accent rule across the very top
      - small uppercase monospace metadata in the top-left / top-right
      - an optional scrolling ticker along the bottom
    No window chrome, no gradients — flat black, restrained.
    """
    # top accent rule
    draw.rectangle([0, 0, w, 3], fill=ACCENT)
    # corner metadata
    if corner_tl:
        draw_text(draw, (28, 26), corner_tl.upper(), font("mono", 15), DIM)
    if corner_tr:
        s = corner_tr.upper()
        draw_text(draw, (w - 28, 26), s, font("mono", 15), DIM, anchor="ra")
    if ticker:
        draw_text(draw, (28, h - 30), ticker.upper(), font("mono", 14), DIM)
    return 52  # content top margin


def brandmark(draw, w, h, label="CLAIMSCOUT"):
    """Small brand lockup, bottom-right, as the reference places its logo."""
    f = font("mono_bold", 16)
    s = f"◆ {label}"
    tw = text_w(draw, s, f)
    draw_text(draw, (w - 28, h - 30), s, f, ACCENT, anchor="ra")


def caption_bar(draw, w, h, text, color=ACCENT):
    """Bottom caption with a colored accent bar."""
    y = h - 64
    draw.rectangle([0, y, w, h], fill=BG_SOFT)
    draw.rectangle([0, y, 6, h], fill=color)
    draw_text(draw, (24, y + 32), text, font("sans_bold", 22), FG, anchor="lm")


# ================================================================ BEAT 1: friction
def beat1(w, h, fps):
    """Persona + high-stakes friction: a wall of dead-end issues (ref style)."""
    dur = 15
    n = dur * fps
    dead = [
        ("#1042", "ASSIGNED", RED),
        ("#1088", "23 COMMENTS — CONTESTED", ORANGE),
        ("#1101", "EPIC · 4 MONTHS OLD", PURPLE),
    ]
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        ref_chrome(draw, w, h, corner_tl="the issue tracker",
                   corner_tr="40 open · 0 claimable")

        # a sparse list of dead issues drifting up, monospace, muted
        y = 90
        for i in range(14):
            num = 1000 + i * 7
            yy = y + i * 40 - int(t * 90)
            if yy < 60 or yy > h - 160:
                continue
            strike = i in (2, 5, 9)  # a few visually "struck out" as taken
            col = DIM
            draw_text(draw, (48, yy), f"#{num}", font("mono", 20), col)
            title = "open issue — already someone else's"
            draw_text(draw, (150, yy), title, font("mono", 18), (70, 70, 74))

        # three big status stamps slam in (t 0.4-0.8), reference "big number" energy
        for j, (num, why, col) in enumerate(dead):
            local = clamp((t - 0.42 - j * 0.12) / 0.12, 0, 1)
            if local <= 0:
                continue
            e = ease_out_back(local)
            bx, by = 90, 300 + j * 110
            x = int(lerp(-500, bx, e))
            draw.rectangle([x, by, x + 7, by + 84], fill=col)  # accent tick
            draw_text(draw, (x + 26, by + 2), num, font("mono_bold", 46), FG)
            draw_text(draw, (x + 28, by + 56), why, font("mono", 18), col)

        # final statement
        slam = clamp((t - 0.85) / 0.1, 0, 1)
        if slam > 0:
            e = ease_out_cubic(slam)
            draw_text(draw, (w // 2, h // 2 + 40), "Sound familiar?",
                      font("sans_bold", int(lerp(72, 60, e))), WHITE, anchor="mm")
        brandmark(draw, w, h)
        yield img


# ================================================================ BEAT 2: reveal
def beat2(w, h, fps):
    """The reveal: flat black, big wordmark, one command (ref style)."""
    dur = 10
    n = dur * fps
    logo = "ClaimScout"
    cmd = "claimscout scan --repos 0dotxyz/marginfi-v2"
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        ref_chrome(draw, w, h, corner_tl="claimscout", corner_tr="v1.0")
        # wordmark springs in
        local = clamp(t / 0.35, 0, 1)
        e = ease_out_back(local)
        lf = font("sans_bold", int(lerp(40, 84, e)))
        s = logo[: int(len(logo) * clamp(t / 0.4, 0, 1))]
        lw = text_w(draw, logo, lf)
        draw_text(draw, (w // 2 - lw / 2, 250), s, lf, FG)
        # accent underline grows beneath the wordmark
        uw = int(lerp(0, lw, clamp((t - 0.35) / 0.25, 0, 1)))
        if uw > 2:
            draw.rectangle([w // 2 - lw / 2, 250 + 96, w // 2 - lw / 2 + uw, 250 + 100],
                           fill=ACCENT)
        # the command, monospace, lower third
        if t > 0.45:
            cs = cmd[: int(len(cmd) * clamp((t - 0.45) / 0.35, 0, 1))]
            draw_text(draw, (90, 430), "$ " + cs, font("mono", 24), FG)
        # tagline
        if t > 0.8:
            draw_text(draw, (90, 500), "Only the issues worth your time.",
                      font("sans", 24), DIM)
        brandmark(draw, w, h)
        yield img


# ================================================================ BEAT 3: live demo + aha
def beat3(w, h, fps):
    """Real scan output streams in; the aha is #682 -> #1 (ref style)."""
    dur = 25
    n = dur * fps
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        ref_chrome(draw, w, h, corner_tl="claimscout scan",
                   corner_tr="0dotxyz/marginfi-v2")

        # scan output, left-aligned monospace, tight hierarchy
        y = 84
        for i, line in enumerate(SCAN_LINES):
            appear = clamp((t - i * 0.05) / 0.05, 0, 1)
            if appear <= 0:
                continue
            if line[0] == "head":
                draw_text(draw, (48, y), line[1], font("mono_bold", 22), FG)
            else:
                _, num, meta, title, labels, col = line
                draw_text(draw, (48, y), num, font("mono_bold", 24), col)
                draw_text(draw, (150, y + 2), title, font("mono", 19), FG)
                draw_text(draw, (150, y + 26), meta, font("mono", 14), DIM)
                draw_text(draw, (48, y + 50), f"· {labels}", font("mono", 14), col)
            y += 88

        # the aha panel on the right: the ranker result, #682 big at top
        if t > 0.6:
            px, py = 760, 84
            e = ease_out_cubic(clamp((t - 0.6) / 0.2, 0, 1))
            panel_h = int(lerp(0, 420, e))
            draw.rectangle([px, py, px + 460, py + panel_h], fill=PANEL)
            draw.rectangle([px, py, px + 460, py + 3], fill=ACCENT)
            if panel_h > 120:
                draw_text(draw, (px + 24, py + 22), "RANKED", font("mono", 14), DIM)
                # #682 as the hero big number
                draw_text(draw, (px + 24, py + 52), "#682", font("sans_bold", 64), GREEN)
                draw_text(draw, (px + 230, py + 78), "[90]", font("mono_bold", 30), GREEN)
                draw_text(draw, (px + 24, py + 128), "good first issue · bounded bug",
                          font("mono", 15), DIM)
                ry = py + 172
                for rank, num, score, reason, col in RANK_LINES[1:]:
                    draw_text(draw, (px + 24, ry), f"{rank} {num} [{score}]",
                              font("mono", 18), col)
                    draw_text(draw, (px + 24, ry + 22), reason[:40],
                              font("mono", 13), (90, 90, 95))
                    ry += 56

        # bottom caption lands the aha in words
        if t > 0.88:
            caption_bar(draw, w, h, "Number one. Hers to take.", GREEN)
        brandmark(draw, w, h)
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
        img, draw = new_frame(w, h)
        ref_chrome(draw, w, h, corner_tl="under the hood", corner_tr="architecture")
        draw_text(draw, (w // 2, 76), "Under the hood", font("sans_bold", 28), FG, anchor="mm")

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
            draw.ellipse([cx - r, ccy - r, cx + r, ccy + r], outline=ACCENT, width=3)
            draw_text(draw, (w // 2, h - 90), label, font("sans_bold", 22), FG, anchor="mm")
        ref_chrome(draw, w, h, corner_tl="architecture", corner_tr="how it works")
        brandmark(draw, w, h)
        yield img


# ================================================================ BEAT 5: montage
def beat5(w, h, fps):
    """Three rapid imperative cuts + a three-up (ref style)."""
    dur = 10
    n = dur * fps
    cards = [
        ("Scan any repo.", "claimscout scan --repos <owner/repo>", CYAN),
        ("Rank on your skills.", "claimscout-rank --profile rust,anchor", GREEN),
        ("Pipe it anywhere.", "claimscout scan --json | jq '.[].number'", PURPLE),
    ]
    for f in range(n):
        t = f / n
        img, draw = new_frame(w, h)
        ref_chrome(draw, w, h, corner_tl="three ways to use it")
        if t < 0.7:
            idx = min(int(t / 0.233), 2)
            local = (t / 0.233) - idx
            title, cmd, col = cards[idx]
            e = ease_out_back(clamp(local / 0.18, 0, 1))
            x = int(lerp(w, 0, e))
            draw.rectangle([x, h // 2 - 70, x + 8, h // 2 + 70], fill=col)
            draw_text(draw, (x + 34, h // 2 - 56), title, font("sans_bold", 56), FG)
            draw_text(draw, (x + 36, h // 2 + 22), cmd, font("mono", 20), DIM)
        else:
            local = clamp((t - 0.7) / 0.15, 0, 1)
            e = ease_out_cubic(local)
            pw = w // 3
            top, bot = 140, h - 140
            for i, (title, cmd, col) in enumerate(cards):
                x = i * pw
                inset = int(lerp(24, 6, e))
                if bot <= top + 20:  # guard tiny canvases
                    top, bot = 40, h - 40
                draw.rectangle([x + inset, top, x + pw - inset, bot], fill=PANEL)
                draw.rectangle([x + inset, top, x + pw - inset, top + 3], fill=col)
                mid = (top + bot) // 2
                draw_text(draw, (x + pw // 2, mid - 30), title,
                          font("sans_bold", 22), FG, anchor="mm")
                draw_text(draw, (x + pw // 2, mid + 14), cmd[:24],
                          font("mono", 13), DIM, anchor="mm")
        brandmark(draw, w, h)
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
            # the merged PR, reference treatment: flat black, metadata top,
            # big "MERGED" statement, real repo + PR number
            ref_chrome(draw, w, h, corner_tl="pull request",
                       corner_tr="genvm-manager")
            draw_text(draw, (48, 90), "fix(manager): report a spawned run as finished",
                      font("sans_bold", 22), FG)
            draw_text(draw, (48, 150), "MERGED", font("sans_bold", 76), GREEN)
            draw_text(draw, (48, 250), "#48   +82  -1   2 files   all checks passed",
                      font("mono", 20), DIM)
            draw_text(draw, (48, 286), "genlayerlabs/genvm-manager",
                      font("mono", 16), DIM)
            if t > 0.18:
                for i in range(20):
                    ang = i * (math.pi * 2 / 20)
                    dist = 100 + (t - 0.18) * 1100
                    cx = 150 + math.cos(ang) * dist
                    cy = 190 + math.sin(ang) * dist * 0.6
                    col = [GREEN, ACCENT, CYAN, PURPLE][i % 4]
                    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=col)
            brandmark(draw, w, h)
        else:
            local = clamp((t - 0.45) / 0.2, 0, 1)
            e = ease_out_back(local)
            lf = font("sans_bold", int(lerp(40, 80, e)))
            logo = "ClaimScout"
            lw = text_w(draw, logo, lf)
            draw_text(draw, (w // 2 - lw / 2, h // 2 - 70), logo, lf, FG)
            draw.rectangle([w // 2 - lw / 2, h // 2 + 30, w // 2 + lw / 2, h // 2 + 34],
                           fill=ACCENT)
            if t > 0.62:
                tl = "Claim what's yours."
                tlw = text_w(draw, tl, font("sans", 28))
                draw_text(draw, (w // 2 - tlw / 2, h // 2 + 70), tl, font("sans", 28), DIM)
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
