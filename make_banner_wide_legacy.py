#!/usr/bin/env python3
"""Generate a green-phosphor CRT terminal banner like yetone's profile README."""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = "/Users/xxuntilu/.dsh/attachments/v1/objects/32/32314cde0850d1637775005d2eb746ded006fe5ce74a339c3ce3580e53850b6e"
OUT = "/Users/xxuntilu/study-ai/agent/crt_avatar/banner.png"

W, H = 1846, 1350
SCAN_H = 30          # one "terminal text line" per scanline block
GAP = 4              # dark gap between scanlines (CRT line spacing)

# ---------- palette (phosphor green + warm highlights) ----------
def hexc(s):
    return tuple(int(s[i:i+2], 16) for i in (1, 3, 5))

BG_DARK   = hexc("#0a1f0d")   # screen background
BG_PANEL  = hexc("#0e2a12")   # slightly lighter panel
GRID_DIM  = hexc("#3f7a3c")   # dim green for empty area
BRIGHT    = hexc("#e8ffe0")   # near-white bright (highlights)
MID       = hexc("#baffb0")
GREEN     = hexc("#59e059")
DIM       = hexc("#2f8f2f")
TEXT      = hexc("#7dffa0")
ORANGE    = hexc("#d98a3a")
PINK      = hexc("#c97a7a")
YELLOW    = hexc("#e8e84a")

def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

# ---------- 1. pixelate the portrait ----------
N_COLS = 46                      # pixel-art width in "character cells"
img = Image.open(SRC).convert("RGB")
# center-crop to square-ish portrait area
w0, h0 = img.size
side = min(w0, h0)
img = img.crop(((w0 - side)//2, (h0 - side)//2, (w0 + side)//2, (h0 + side)//2))
N_ROWS = int(N_COLS * img.size[1] / img.size[0])
small = img.resize((N_COLS, N_ROWS), Image.LANCZOS)
arr = np.asarray(small).astype(float)

# brightness -> green intensity
lum = arr @ [0.299, 0.587, 0.114] / 255.0

# ---------- 2. build the big canvas ----------
canvas = Image.new("RGB", (W, H), BG_DARK)
draw = ImageDraw.Draw(canvas)

# left portrait area occupies left 55%
PX = int(W * 0.545 / N_COLS)     # pixel-cell width in screen px
cell_h = SCAN_H                  # each art row spans one scanline (with gap)

# subtle vignette background: radial gradient
yy, xx = np.mgrid[0:H, 0:W]
cx, cy = W * 0.5, H * 0.45
dist = np.sqrt(((xx - cx) / (W/2))**2 + ((yy - cy) / (H/2))**2)
vig = np.clip(1.15 - dist * 0.55, 0, 1)
panel = np.zeros((H, W, 3), dtype=float)
panel[:, :] = BG_PANEL
vig_img = Image.fromarray((panel * vig[..., None]).astype(np.uint8), "RGB")
canvas = Image.blend(canvas, vig_img, 0.55)
draw = ImageDraw.Draw(canvas)

# ---------- 3. draw the pixel-art portrait with scanline gaps ----------
ox = int(W * 0.04)
oy = int(H * 0.03)
for r in range(N_ROWS):
    y0 = oy + r * cell_h
    for c in range(N_COLS):
        L = lum[r, c]
        x0 = ox + c * PX
        if L < 0.16:
            # very dark: faint alternating stripe (background scanline texture)
            stripe = 0.55 if r % 2 == 0 else 0.30
            col = lerp(BG_DARK, GRID_DIM, 0.10 * stripe)
            draw.rectangle([x0 + 1, y0, x0 + PX - 1, y0 + SCAN_H - GAP], fill=col)
            continue
        # map brightness to palette
        if L > 0.75:
            col = lerp(MID, BRIGHT, (L - 0.75) / 0.25)
        elif L > 0.45:
            col = lerp(GREEN, MID, (L - 0.45) / 0.30)
        else:
            col = lerp(DIM, GREEN, (L - 0.16) / 0.29)
        # per-cell horizontal stripes to mimic char-block texture
        draw.rectangle([x0 + 1, y0, x0 + PX - 1, y0 + SCAN_H - GAP], fill=col)
        # darker sub-lines inside cell for texture
        if L < 0.6:
            draw.line([x0 + 1, y0 + SCAN_H//2, x0 + PX - 1, y0 + SCAN_H//2],
                      fill=lerp(col, BG_DARK, 0.35), width=2)

# ---------- 4. glow / bloom ----------
glow = canvas.filter(ImageFilter.GaussianBlur(7))
canvas = Image.blend(canvas, glow, 0.35)
draw = ImageDraw.Draw(canvas)

# ---------- 5. right side text ----------
def load_font(size):
    for p in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.dfont",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()

FS = 34
font = load_font(FS)
tx = int(W * 0.60)
ty = int(H * 0.06)
lh = int(FS * 1.45)

def txt(x, y, s, col=TEXT, font=font):
    # slight glow: draw text 3x with blur behind
    draw.text((x, y), s, fill=col, font=font)

lines = [
    ("Name:", "XXuntilu"),
    ("Age:", "17"),
    ("Work:", "QA Engineer (SDET)"),
    ("OS:", "macOS"),
    ("Editor:", "Neovim"),
]
y = ty
for k, v in lines:
    txt(tx, y, k, TEXT)
    txt(tx + 8 * FS, y, v, BRIGHT if k != "Name:" else TEXT)
    y += lh

# Languages (wrapped)
txt(tx, y, "Languages:", TEXT)
langs = "Python, JavaScript,\nTypeScript, Shell"
y += lh
for part in langs.split("\n"):
    txt(tx + 5 * FS, y, part, BRIGHT)
    y += int(lh * 0.95)

y += 10
txt(tx, y, "Skills:", TEXT)
skills = "QA / Test Dev,\nAutomation,\nTooling"
y += lh
for part in skills.split("\n"):
    txt(tx + 5 * FS, y, part, BRIGHT)
    y += int(lh * 0.95)

# ---------- 6. contribution heatmap strip ----------
hy = y + 40
hx = tx + 5 * FS
cell = 36
rng = np.random.default_rng(42)
levels = [None, DIM, GREEN, MID, YELLOW, ORANGE, PINK]
heat_cols = 10
grid = rng.integers(0, 7, size=(2, heat_cols))
for r in range(2):
    for c in range(heat_cols):
        lv = grid[r, c]
        x0 = hx + c * cell
        y0 = hy + r * cell
        if lv == 0:
            draw.rectangle([x0+1, y0+1, x0+cell-2, y0+cell-2], fill=lerp(BG_DARK, GRID_DIM, 0.18))
        else:
            # glow via layered rects
            base = levels[lv]
            draw.rectangle([x0-2, y0-2, x0+cell+1, y0+cell+1], fill=lerp(base, BRIGHT, 0.35))
            draw.rectangle([x0+1, y0+1, x0+cell-2, y0+cell-2], fill=base)

# ---------- 7. scanlines + screen vignette overlay ----------
overlay = Image.new("L", (W, H), 0)
odraw = ImageDraw.Draw(overlay)
for yl in range(0, H, SCAN_H):
    odraw.line([0, yl + SCAN_H - GAP, W, yl + SCAN_H - GAP], fill=90, width=GAP)
dark = Image.new("RGB", (W, H), (0, 0, 0))
canvas = Image.composite(dark, canvas, overlay.point(lambda v: v))

# rounded screen mask + inner shadow
mask = Image.new("L", (W, H), 0)
mdraw = ImageDraw.Draw(mask)
rad = 40
mdraw.rounded_rectangle([10, 10, W - 10, H - 10], radius=rad, fill=255)
final = Image.new("RGB", (W, H), (0, 0, 0))
final.paste(canvas, (0, 0), mask)

# outer glow of the whole screen
edge_glow = final.filter(ImageFilter.GaussianBlur(18))
final = Image.blend(final, edge_glow, 0.25)
final.paste(canvas, (0, 0), mask)

# scanline sheen: add faint bright lines
sheen = np.asarray(final).astype(float)
for yl in range(0, H, SCAN_H):
    sheen[yl:yl+1, :, 1] = np.clip(sheen[yl:yl+1, :, 1] + 14, 0, 255)
final = Image.fromarray(sheen.astype(np.uint8))

final.save(OUT, "PNG")
print("saved", OUT)
