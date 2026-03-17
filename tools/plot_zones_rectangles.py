#!/usr/bin/env python3
"""
Карта зон Шамалган в виде прямоугольников (сетка 10×8 в WGS84).
Заливка по home_weight из zones-derived.csv. Результат: Visualization/zone-derivation/08_zones_rectangles.png
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV = ROOT / "Visualization" / "zone-derivation" / "summary_new_map.csv"
ZONES_CSV = ROOT / "original-input-data" / "shamalgan" / "zones-derived.csv"
OSM_MAP = ROOT / "original-input-data" / "shamalgan" / "map"
OUT_PNG = ROOT / "Visualization" / "zone-derivation" / "08_zones_rectangles.png"
ZONE_COLS = 10
ZONE_ROWS = 8


def read_bbox(path: Path) -> tuple[float, float, float, float]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        row = next(r)
    return (
        float(row["bbox_minlon"]),
        float(row["bbox_maxlon"]),
        float(row["bbox_minlat"]),
        float(row["bbox_maxlat"]),
    )


def read_zones(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            out.append({
                "zone_id": row.get("zone_id", ""),
                "home_x": float(row["home_x"]),
                "home_y": float(row["home_y"]),
                "home_weight": float(row["home_weight"]),
            })
    return out


def collect_highway_lines(osm_path: Path) -> list:
    import xml.etree.ElementTree as ET
    tree = ET.parse(osm_path)
    root = tree.getroot()
    nodes = {}
    for n in root.findall("node"):
        nid = n.attrib.get("id")
        if nid is None:
            continue
        nodes[nid] = (float(n.attrib["lon"]), float(n.attrib["lat"]))
    lines = []
    for w in root.findall("way"):
        if not any(tag.attrib.get("k") == "highway" for tag in w.findall("tag")):
            continue
        pts = []
        for nd in w.findall("nd"):
            ref = nd.attrib.get("ref")
            if ref in nodes:
                pts.append(nodes[ref])
        if len(pts) >= 2:
            lines.append(pts)
    return lines


def main():
    minlon, maxlon, minlat, maxlat = read_bbox(SUMMARY_CSV)
    lon_edges = np.linspace(minlon, maxlon, ZONE_COLS + 1)
    lat_edges = np.linspace(minlat, maxlat, ZONE_ROWS + 1)

    transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    zones = read_zones(ZONES_CSV)

    # weight[row, col] in row-major: row 0 = northernmost (lat_edges[0]..lat_edges[1])
    # lat_edges[0] = maxlat, lat_edges[8] = minlat (if linspace(minlat, maxlat, 9) then lat_edges[0]=minlat)
    # So row 0 = minlat..lat_edges[1], row 7 = lat_edges[7]..maxlat. Actually np.linspace(minlat, maxlat, 9) gives minlat first.
    # So row index: lat_edges[i] <= lat < lat_edges[i+1] -> row = i. But then row 0 is southernmost. For plot we want row 0 at top (north). So we use (ZONE_ROWS - 1 - row) for plotting or flip the matrix. Let me assign weight[col][row] as (lon col, lat row) with row 0 = south; then when we draw we'll do ax.imshow(..., extent=[minlon,maxlon,minlat,maxlat], aspect='auto') or draw rects. Actually drawing rects: for col in 0..9, row in 0..7, the rectangle is [lon_edges[col], lon_edges[col+1]] x [lat_edges[row], lat_edges[row+1]]. So we need a 8x10 matrix where grid[row, col] = home_weight for the cell (row, col). lat_edges[0]=minlat, lat_edges[8]=maxlat. So cell (row=0, col=0) is SW corner. I'll fill grid[row, col] and then when plotting use origin='lower' so row 0 at bottom.
    grid = np.full((ZONE_ROWS, ZONE_COLS), np.nan)

    for z in zones:
        lon, lat = transformer.transform(z["home_x"], z["home_y"])
        if not (minlon <= lon <= maxlon and minlat <= lat <= maxlat):
            continue
        col = np.searchsorted(lon_edges, lon, side="right") - 1
        row = np.searchsorted(lat_edges, lat, side="right") - 1
        if 0 <= col < ZONE_COLS and 0 <= row < ZONE_ROWS:
            if np.isnan(grid[row, col]):
                grid[row, col] = z["home_weight"]
            else:
                grid[row, col] += z["home_weight"]

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_aspect("equal")

    # Optional: OSM roads (thin lines)
    if OSM_MAP.exists():
        try:
            lines = collect_highway_lines(OSM_MAP)
            for pts in lines:
                lons = [p[0] for p in pts]
                lats = [p[1] for p in pts]
                ax.plot(lons, lats, color="#cccccc", linewidth=0.4, zorder=0)
        except Exception:
            pass

    cmap = plt.get_cmap("YlOrRd")
    vmin = 0
    vmax = np.nanmax(grid) if np.any(np.isfinite(grid)) else 1
    norm = Normalize(vmin=vmin, vmax=vmax)

    for row in range(ZONE_ROWS):
        for col in range(ZONE_COLS):
            x0, x1 = lon_edges[col], lon_edges[col + 1]
            y0, y1 = lat_edges[row], lat_edges[row + 1]
            w = grid[row, col]
            if np.isfinite(w) and w > 0:
                color = cmap(norm(w))
            else:
                color = "#f0f0f0"
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=color, edgecolor="#666666", linewidth=0.6))

    ax.set_xlim(minlon, maxlon)
    ax.set_ylim(minlat, maxlat)
    ax.set_xlabel("Долгота (WGS84)")
    ax.set_ylabel("Широта (WGS84)")
    ax.set_title("Зональная сетка населения — Шамалган (10×8), прямоугольники")
    cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=0.7, label="Население (home_weight)")
    cbar.ax.set_ylabel("Население (home_weight)", fontsize=10)
    fig.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
