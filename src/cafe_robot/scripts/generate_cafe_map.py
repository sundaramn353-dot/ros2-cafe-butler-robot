#!/usr/bin/env python3
"""
generate_cafe_map.py — Generate a PGM occupancy grid map matching cafe_world.sdf.

Map specs:
  - Café: 10m × 8m  (X: -5 to +5, Y: -4 to +4)
  - Resolution: 0.05 m/pixel → 200 × 160 pixels
  - Origin: (-5.0, -4.0, 0.0)

PGM values:
  - 254 = free space (white)
  - 0   = occupied (black)
  - 205 = unknown (grey)

Run:
    python3 generate_cafe_map.py
"""

import struct
import os

# Map dimensions
RESOLUTION = 0.05  # m/pixel
ORIGIN_X = -5.0
ORIGIN_Y = -4.0
WIDTH_M = 10.0
HEIGHT_M = 8.0
WIDTH_PX = int(WIDTH_M / RESOLUTION)   # 200
HEIGHT_PX = int(HEIGHT_M / RESOLUTION)  # 160

FREE = 254
OCCUPIED = 0
WALL_THICKNESS = 3  # pixels (~0.15m)


def world_to_pixel(wx, wy):
    """Convert world coords to pixel coords."""
    px = int((wx - ORIGIN_X) / RESOLUTION)
    py = int((wy - ORIGIN_Y) / RESOLUTION)
    return px, py


def fill_rect(grid, cx, cy, w, h):
    """Fill a rectangle centered at (cx, cy) with size (w, h) in world coords."""
    x1, y1 = world_to_pixel(cx - w / 2, cy - h / 2)
    x2, y2 = world_to_pixel(cx + w / 2, cy + h / 2)
    x1, x2 = max(0, x1), min(WIDTH_PX - 1, x2)
    y1, y2 = max(0, y1), min(HEIGHT_PX - 1, y2)
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            grid[y][x] = OCCUPIED


def fill_circle(grid, cx, cy, radius):
    """Fill a circle centered at (cx, cy) with given radius in world coords."""
    px, py = world_to_pixel(cx, cy)
    r_px = int(radius / RESOLUTION)
    for dy in range(-r_px, r_px + 1):
        for dx in range(-r_px, r_px + 1):
            if dx * dx + dy * dy <= r_px * r_px:
                nx, ny = px + dx, py + dy
                if 0 <= nx < WIDTH_PX and 0 <= ny < HEIGHT_PX:
                    grid[ny][nx] = OCCUPIED


def main():
    # Initialize all pixels as free
    grid = [[FREE for _ in range(WIDTH_PX)] for _ in range(HEIGHT_PX)]

    # ── Outer walls ──────────────────────────────────────────────
    # North wall: y=4, full width
    fill_rect(grid, 0.0, 4.0, 10.3, 0.15)
    # South wall: y=-4
    fill_rect(grid, 0.0, -4.0, 10.3, 0.15)
    # East wall: x=5
    fill_rect(grid, 5.0, 0.0, 0.15, 8.0)
    # West wall: x=-5
    fill_rect(grid, -5.0, 0.0, 0.15, 8.0)

    # ── Kitchen walls ────────────────────────────────────────────
    # Kitchen south counter wall
    fill_rect(grid, -3.25, 1.5, 3.5, 0.15)
    # Kitchen east counter wall
    fill_rect(grid, -1.5, 2.95, 0.15, 2.1)
    # Kitchen countertop
    fill_rect(grid, -4.2, 2.75, 1.4, 0.6)

    # ── Tables (tabletop + chairs) ───────────────────────────────
    # Table 1 at (2.5, 2.5)
    fill_rect(grid, 2.5, 2.5, 0.8, 0.8)    # tabletop
    fill_rect(grid, 1.8, 2.5, 0.4, 0.4)    # chair a
    fill_rect(grid, 3.2, 2.5, 0.4, 0.4)    # chair b

    # Table 2 at (2.5, 0.0)
    fill_rect(grid, 2.5, 0.0, 0.8, 0.8)
    fill_rect(grid, 1.8, 0.0, 0.4, 0.4)
    fill_rect(grid, 3.2, 0.0, 0.4, 0.4)

    # Table 3 at (2.5, -2.5)
    fill_rect(grid, 2.5, -2.5, 0.8, 0.8)
    fill_rect(grid, 1.8, -2.5, 0.4, 0.4)
    fill_rect(grid, 3.2, -2.5, 0.4, 0.4)

    # ── Obstacles ────────────────────────────────────────────────
    # Shelf at (-3.5, -3.0)
    fill_rect(grid, -3.5, -3.0, 0.8, 0.4)
    # Planter at (0.0, -2.0) — circular
    fill_circle(grid, 0.0, -2.0, 0.25)
    # Trash bin at (-1.0, 0.8) — circular
    fill_circle(grid, -1.0, 0.8, 0.18)
    # Display stand at (0.5, 1.5)
    fill_rect(grid, 0.5, 1.5, 0.5, 0.5)

    # ── Write PGM (P5 binary) ───────────────────────────────────
    script_dir = os.path.dirname(os.path.abspath(__file__))
    maps_dir = os.path.join(script_dir, '..', 'maps')
    os.makedirs(maps_dir, exist_ok=True)

    pgm_path = os.path.join(maps_dir, 'cafe_map.pgm')
    with open(pgm_path, 'wb') as f:
        header = f'P5\n{WIDTH_PX} {HEIGHT_PX}\n255\n'
        f.write(header.encode('ascii'))
        for row in grid:
            f.write(bytes(row))

    print(f'✅  Generated {pgm_path}  ({WIDTH_PX}×{HEIGHT_PX} px)')

    # ── Write YAML ───────────────────────────────────────────────
    yaml_path = os.path.join(maps_dir, 'cafe_map.yaml')
    yaml_content = f"""image: cafe_map.pgm
mode: trinary
resolution: {RESOLUTION}
origin: [{ORIGIN_X}, {ORIGIN_Y}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f'✅  Generated {yaml_path}')


if __name__ == '__main__':
    main()
