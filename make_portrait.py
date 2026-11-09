#!/usr/bin/env python3
"""Portrait-only green-phosphor CRT image (no text). Text lives in README.md."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = "/Users/xxuntilu/.dsh/attachments/v1/objects/32/32314cde0850d1637775005d2eb746ded006fe5ce74a339c3ce3580e53850b6e"
OUT = "/Users/xxuntilu/study-ai/agent/crt_avatar/banner.png"

W = H = 1200
SCAN_H = 30
GAP = 4


def hexc(s):
    return tuple(int(s[i:i+2], 16) for i in (1, 3, 5))


BG_DARK  = hexc("#0a1f0d")
BG_PANEL = hexc("#0e2a12")
GRID_DIM = hexc("#3f7a3c")
BRIGHT   = hexc("#e8ffe0")
MID      = hexc("#baffb0")
GREEN    = hexc("#59e059")
DIM      = hexc("#2f8f2f")


def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ---------- pixelate ----------
N_COLS = 62
img = Image.open(SRC).convert("RGB")
w0, h0 = img.size
# tighter crop on the subject: (left, top, right, bottom) as fractions
cx0, cy0, cx1, cy1 = 0.03, 0.03, 0.97, 0.99
img = img.crop((int(w0*cx0), int(h0*cy0), int(w0*cx1), int(h0*cy1)))
N_ROWS = int(N_COLS * img.size[1] / img.size[0])
img = img.filter(ImageFilter.UnsharpMask(radius=28, percent=170, threshold=2))
small = img.resize((N_COLS, N_ROWS), Image.LANCZOS)
arr = np.asarray(small).astype(float)
lum = arr @ [0.299, 0.587, 0.114] / 255.0
# S-curve: background/sky sinks to dim green, face highlights blow out bright
lum = np.clip(0.5 + (lum - 0.44) * 1.15, 0, 1)

# palette ramp: intensity -> phosphor color
STOPS = [(0.00, hexc("#081a0a")), (0.22, hexc("#1d5c22")),
         (0.45, hexc("#3fa63f")), (0.70, hexc("#8fe88f")),
         (1.00, hexc("#eaffee"))]

def ramp(v):
    v = min(max(v, 0.0), 1.0)
    for (p0, c0), (p1, c1) in zip(STOPS, STOPS[1:]):
        if v <= p1:
            t = 0 if p1 == p0 else (v - p0) / (p1 - p0)
            return lerp(c0, c1, t)
    return STOPS[-1][1]

# ---------- canvas ----------
canvas = Image.new("RGB", (W, H), BG_DARK)
yy, xx = np.mgrid[0:H, 0:W]
cx, cy = W * 0.5, H * 0.45
dist = np.sqrt(((xx - cx) / (W/2))**2 + ((yy - cy) / (H/2))**2)
vig = np.clip(1.15 - dist * 0.55, 0, 1)
panel = np.zeros((H, W, 3), dtype=float)
panel[:, :] = BG_PANEL
vig_img = Image.fromarray((panel * vig[..., None]).astype(np.uint8), "RGB")
canvas = Image.blend(canvas, vig_img, 0.55)
draw = ImageDraw.Draw(canvas)

# ---------- portrait, centered ----------
art_w = W * 0.86
PX = art_w / N_COLS
ox = (W - art_w) / 2
art_h = N_ROWS * SCAN_H
oy = (H - art_h) / 2

for r in range(N_ROWS):
    y0 = oy + r * SCAN_H
    for c in range(N_COLS):
        L = lum[r, c]
        x0 = ox + c * PX
        col = ramp(L)
        # CRT raster: faint darker line inside each cell
        draw.rectangle([x0 + 1, y0, x0 + PX - 1, y0 + SCAN_H - GAP], fill=col)
        if L < 0.55:
            draw.line([x0 + 1, y0 + SCAN_H//2, x0 + PX - 1, y0 + SCAN_H//2],
                      fill=lerp(col, hexc("#051206"), 0.30), width=2)

# ---------- bloom ----------
glow = canvas.filter(ImageFilter.GaussianBlur(7))
canvas = Image.blend(canvas, glow, 0.35)

# ---------- scanlines ----------
overlay = Image.new("L", (W, H), 0)
odraw = ImageDraw.Draw(overlay)
for yl in range(0, H, SCAN_H):
    odraw.line([0, yl + SCAN_H - GAP, W, yl + SCAN_H - GAP], fill=90, width=GAP)
dark = Image.new("RGB", (W, H), (0, 0, 0))
canvas = Image.composite(dark, canvas, overlay)

# ---------- rounded screen ----------
mask = Image.new("L", (W, H), 0)
mdraw = ImageDraw.Draw(mask)
mdraw.rounded_rectangle([10, 10, W - 10, H - 10], radius=40, fill=255)
final = Image.new("RGB", (W, H), (0, 0, 0))
final.paste(canvas, (0, 0), mask)
edge_glow = final.filter(ImageFilter.GaussianBlur(18))
final = Image.blend(final, edge_glow, 0.25)
final.paste(canvas, (0, 0), mask)

sheen = np.asarray(final).astype(float)
for yl in range(0, H, SCAN_H):
    sheen[yl:yl+1, :, 1] = np.clip(sheen[yl:yl+1, :, 1] + 14, 0, 255)
final = Image.fromarray(sheen.astype(np.uint8))

final.save(OUT, "PNG")
print("saved", OUT, final.size)
