#!/usr/bin/env python3
"""
gen_map.py — Generate cafe_map.pgm matching cafe_world.sdf.

PGM convention:
  - Row 0 = TOP of image = HIGHEST Y in world
  - map_server origin = bottom-left pixel in world coords

Map: 10m × 8m, resolution 0.05m/px → 200 × 160 pixels
"""
import os

RESOLUTION = 0.05
ORIGIN_X, ORIGIN_Y = -5.0, -4.0
W, H = 200, 160  # pixels
FREE, OCC = 254, 0


def w2p(wx, wy):
    """World → pixel. Y is flipped for PGM (row 0 = top = max Y)."""
    px = int((wx - ORIGIN_X) / RESOLUTION)
    py = (H - 1) - int((wy - ORIGIN_Y) / RESOLUTION)  # FLIP Y
    return px, py


def fill_rect(g, cx, cy, w, h):
    """Fill rectangle centered at (cx, cy) world coords."""
    # Get corners in pixel coords
    x1, _ = w2p(cx - w / 2, 0)
    x2, _ = w2p(cx + w / 2, 0)
    _, y1 = w2p(0, cy + h / 2)   # top of rect → smaller py (PGM row)
    _, y2 = w2p(0, cy - h / 2)   # bottom of rect → larger py
    x1, x2 = max(0, min(x1, x2)), min(W - 1, max(x1, x2))
    y1, y2 = max(0, min(y1, y2)), min(H - 1, max(y1, y2))
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            g[y * W + x] = OCC


def fill_circ(g, cx, cy, r):
    """Fill circle centered at (cx, cy) world coords."""
    px, py = w2p(cx, cy)
    rp = int(r / RESOLUTION)
    for dy in range(-rp, rp + 1):
        for dx in range(-rp, rp + 1):
            if dx * dx + dy * dy <= rp * rp:
                nx, ny = px + dx, py + dy
                if 0 <= nx < W and 0 <= ny < H:
                    g[ny * W + nx] = OCC


g = bytearray([FREE] * (W * H))

# ── Outer walls ──────────────────────────────────────────────
fill_rect(g, 0.0, 4.0, 10.3, 0.15)     # North
fill_rect(g, 0.0, -4.0, 10.3, 0.15)    # South
fill_rect(g, 5.0, 0.0, 0.15, 8.0)      # East
fill_rect(g, -5.0, 0.0, 0.15, 8.0)     # West

# ── Kitchen ──────────────────────────────────────────────────
fill_rect(g, -3.25, 1.5, 3.5, 0.15)    # South counter wall
fill_rect(g, -1.5, 3.25, 0.15, 1.5)    # East counter wall
fill_rect(g, -4.2, 2.75, 1.4, 0.6)     # Countertop

# ── Tables + chairs ─────────────────────────────────────────
for ty in [2.5, 0.0, -2.5]:
    fill_rect(g, 2.5, ty, 0.8, 0.8)    # Table top
    fill_rect(g, 1.8, ty, 0.4, 0.4)    # Chair A
    fill_rect(g, 3.2, ty, 0.4, 0.4)    # Chair B

# ── Obstacles ────────────────────────────────────────────────
fill_rect(g, -3.5, -3.0, 0.8, 0.4)     # Shelf
fill_circ(g, 0.0, -2.0, 0.25)          # Planter
fill_circ(g, -1.0, 0.8, 0.18)          # Trash bin
fill_rect(g, 0.5, 1.5, 0.5, 0.5)       # Display stand

# ── Write PGM ───────────────────────────────────────────────
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '..', 'maps', 'cafe_map.pgm')
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'wb') as f:
    f.write(f'P5\n{W} {H}\n255\n'.encode())
    f.write(bytes(g))

print(f'✅ {out} ({W}×{H} px, origin=({ORIGIN_X},{ORIGIN_Y}))')
