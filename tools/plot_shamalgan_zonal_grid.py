#!/usr/bin/env python3
"""
Plot a 10×8 zonal grid heatmap for Shamalgan based on zones-derived.csv and the MATSim network.

Output:
- docs/ru/progress/img/zones_population_heatmap.png

The goal is to produce a cartographic image close to
«Зональная сетка населения — Шамалган (10×8)», but using real data:
- grid cells = 10 (cols) × 8 (rows)
- color = home_weight per zone
- overlay = road network outline from scenarios/shamalgan/network.xml
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
ZONES_CSV = ROOT / "original-input-data" / "shamalgan" / "zones-derived.csv"
NETWORK_XML = ROOT / "scenarios" / "shamalgan" / "network.xml"
OUT_IMG = ROOT / "docs" / "ru" / "progress" / "img" / "zones_population_heatmap.png"

# These must match derive_shamalgan_zones.py
ZONE_COLS = 10
ZONE_ROWS = 8


def load_zones(path: Path):
    zones = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                zid = row["zone_id"].strip()
                home_x = float(row["home_x"])
                home_y = float(row["home_y"])
                home_weight = float(row["home_weight"])
            except (KeyError, ValueError):
                continue
            zones.append({"zone_id": zid, "home_x": home_x, "home_y": home_y, "home_weight": home_weight})
    return zones


def load_network_segments(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    nodes = {}
    for n in root.findall(".//node"):
        nid = n.attrib.get("id")
        if not nid:
            continue
        nodes[nid] = (float(n.attrib["x"]), float(n.attrib["y"]))
    segments = []
    for link in root.findall(".//link"):
        fr = link.attrib.get("from")
        to = link.attrib.get("to")
        if not fr or not to:
            continue
        if fr not in nodes or to not in nodes:
            continue
        segments.append((nodes[fr], nodes[to]))
    return segments


def build_grid_from_zones(zones):
    """
    Reconstruct 10×8 grid using zone_id order from derive_shamalgan_zones:
    zone_id = z{num:02d}, num increases row-major (rows 0..7, cols 0..9),
    even for empty cells (they were just skipped in CSV).
    """
    grid = np.full((ZONE_ROWS, ZONE_COLS), np.nan, dtype=float)
    # Also compute bounding box from centroids
    xs, ys = [], []
    for z in zones:
        zid = z["zone_id"]
        try:
            num = int(zid[1:])
        except ValueError:
            continue
        idx = num - 1
        r = idx // ZONE_COLS
        c = idx % ZONE_COLS
        if 0 <= r < ZONE_ROWS and 0 <= c < ZONE_COLS:
            grid[r, c] = z["home_weight"]
        xs.append(z["home_x"])
        ys.append(z["home_y"])
    if not xs or not ys:
        raise RuntimeError("No valid zones found in zones-derived.csv")
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    # Small padding so grid isn't tight to border
    pad_x = (max_x - min_x) * 0.05
    pad_y = (max_y - min_y) * 0.05
    return grid, (min_x - pad_x, max_x + pad_x, min_y - pad_y, max_y + pad_y)


def plot_zonal_grid():
    zones = load_zones(ZONES_CSV)
    segments = load_network_segments(NETWORK_XML)
    grid, (min_x, max_x, min_y, max_y) = build_grid_from_zones(zones)

    # Prepare colormap bins ~ to previous manual visualization
    vmax = np.nanmax(grid)
    bins = [1, 100, 300, 500, 700, 900, 1100, max(1300, vmax + 1)]
    cmap = matplotlib.cm.get_cmap("YlOrRd", len(bins) - 1)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)

    # Draw grid as pcolormesh in EPSG:32643 coordinates
    xs = np.linspace(min_x, max_x, ZONE_COLS + 1)
    ys = np.linspace(min_y, max_y, ZONE_ROWS + 1)
    X, Y = np.meshgrid(xs, ys)

    # Map numeric grid to bin indices
    grid_plot = np.zeros_like(grid)
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        mask = (grid >= lo) & (grid < hi)
        grid_plot[mask] = i + 1

    # flip vertically so row 0 is at top visually
    mesh = ax.pcolormesh(X, Y, np.flipud(grid_plot), cmap=cmap, shading="auto")

    # Overlay road network to show real Shamalgan outline
    for (x1, y1), (x2, y2) in segments:
        ax.plot([x1, x2], [y1, y2], color="#333333", linewidth=0.6, alpha=0.9)

    ax.set_aspect("equal")
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title("Зональная сетка населения — Шамалган (10×8)", fontsize=11, loc="left")
    ax.text(
        0.02,
        0.05,
        "EPSG:32643",
        transform=ax.transAxes,
        fontsize=7,
        color="#555555",
    )
    ax.text(
        0.8,
        0.95,
        "sigma_m = 300 м",
        transform=ax.transAxes,
        fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#555555"),
    )

    # Colorbar with Russian labels
    cax = fig.add_axes([0.82, 0.2, 0.03, 0.6])
    cb = fig.colorbar(
        matplotlib.cm.ScalarMappable(cmap=cmap, norm=matplotlib.colors.BoundaryNorm(bins, cmap.N)),
        cax=cax,
        boundaries=bins,
        ticks=[(bins[i] + bins[i + 1]) / 2 for i in range(len(bins) - 1)],
    )
    cb.ax.set_yticklabels(
        [
            "1 - 100",
            "100 - 300",
            "300 - 500",
            "500 - 700",
            "700 - 900",
            "900 - 1100",
            "1100+",
        ]
    )
    cb.ax.set_title("Население\n(home_weight)", fontsize=7)

    OUT_IMG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0.04, 0.04, 0.8, 0.96])
    fig.savefig(OUT_IMG, dpi=150)
    plt.close(fig)
    print(f"Saved zonal grid map: {OUT_IMG}")


if __name__ == "__main__":
    plot_zonal_grid()

