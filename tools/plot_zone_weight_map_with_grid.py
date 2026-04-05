#!/usr/bin/env python3
"""
Plot the zone centroid weight map with an explicit rectangular zoning grid overlay.

Why this exists:
- `Visualization/zone-derivation/06_zone_weight_map.png` shows only centroids (points).
- The actual zones are rectangular grid cells (ZONE_COLS x ZONE_ROWS) within the OSM bounds.
- This script renders the same map but adds grid lines to remove ambiguity.

Inputs (defaults match Shamalgan):
- original-input-data/<city>/map               (OSM XML with <bounds>)
- original-input-data/<city>/zones-derived.csv (home/work weights + centroids in TARGET_CRS)

Output:
- Visualization/zone-derivation/06_zone_weight_map_with_grid.png
"""

from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer


# =========================
# USER VARIABLES (edit here)
# =========================
ROOT = Path(__file__).resolve().parents[1]
CITY = "shamalgan"

OSM_PATH = ROOT / "original-input-data" / CITY / "map"
ZONES_CSV = ROOT / "original-input-data" / CITY / "zones-derived.csv"
OUT_PNG = ROOT / "Visualization" / "zone-derivation" / "06_zone_weight_map_with_grid.png"

# Grid definition (must match zone derivation).
ZONE_COLS = 10
ZONE_ROWS = 8

# CRS used for network/population coordinates in this project.
TARGET_CRS = "EPSG:32643"


def parse_bounds_from_osm(osm_path: Path) -> tuple[float, float, float, float]:
    tree = ET.parse(osm_path)
    root = tree.getroot()
    bounds = root.find("bounds")
    if bounds is None:
        raise RuntimeError(f"No <bounds> found in OSM file: {osm_path}")
    minlat = float(bounds.attrib["minlat"])
    minlon = float(bounds.attrib["minlon"])
    maxlat = float(bounds.attrib["maxlat"])
    maxlon = float(bounds.attrib["maxlon"])
    return minlon, maxlon, minlat, maxlat


def collect_highway_lines(osm_path: Path) -> list[np.ndarray]:
    tree = ET.parse(osm_path)
    root = tree.getroot()
    nodes: dict[str, tuple[float, float]] = {}
    for n in root.findall("node"):
        nid = n.attrib.get("id")
        if nid is None:
            continue
        nodes[nid] = (float(n.attrib["lon"]), float(n.attrib["lat"]))

    lines: list[np.ndarray] = []
    for w in root.findall("way"):
        has_highway = any(tag.attrib.get("k") == "highway" for tag in w.findall("tag"))
        if not has_highway:
            continue
        pts: list[tuple[float, float]] = []
        for nd in w.findall("nd"):
            ref = nd.attrib.get("ref")
            if ref in nodes:
                pts.append(nodes[ref])
        if len(pts) >= 2:
            lines.append(np.asarray(pts, dtype=float))
    return lines


def read_zones(zones_csv: Path) -> list[dict]:
    """
    Read zones-derived.csv and convert centroid coords back to lon/lat for plotting.
    zones-derived.csv stores home_x/home_y in TARGET_CRS (meters), so we inverse-transform.
    """
    if not zones_csv.exists():
        raise FileNotFoundError(zones_csv)

    tx_inv = Transformer.from_crs(TARGET_CRS, "EPSG:4326", always_xy=True)
    out: list[dict] = []
    with zones_csv.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                x = float(row["home_x"])
                y = float(row["home_y"])
                hw = float(row["home_weight"])
            except Exception:
                continue
            lon, lat = tx_inv.transform(x, y)
            out.append(
                {
                    "zone_id": row.get("zone_id", ""),
                    "lon": float(lon),
                    "lat": float(lat),
                    "home_weight": hw,
                }
            )
    return out


def plot(out_path: Path, roads: list[np.ndarray], zones: list[dict], bounds: tuple[float, float, float, float]) -> None:
    minlon, maxlon, minlat, maxlat = bounds
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build grid lines in lon/lat.
    lon_edges = np.linspace(minlon, maxlon, ZONE_COLS + 1)
    lat_edges = np.linspace(minlat, maxlat, ZONE_ROWS + 1)

    plt.figure(figsize=(12, 7))

    # Roads (same styling as derive_shamalgan_zones.py)
    for line in roads:
        plt.plot(line[:, 0], line[:, 1], color="#d4a72c", linewidth=1.0, alpha=0.8, zorder=1)

    # Grid overlay (thin, subtle)
    for lo in lon_edges:
        plt.plot([lo, lo], [minlat, maxlat], color="#111827", linewidth=0.6, alpha=0.22, zorder=2)
    for la in lat_edges:
        plt.plot([minlon, maxlon], [la, la], color="#111827", linewidth=0.6, alpha=0.22, zorder=2)

    # Zone centroids
    if zones:
        weights = np.array([z["home_weight"] for z in zones], dtype=float)
        denom = float(np.nanmax(weights)) if np.isfinite(np.nanmax(weights)) and np.nanmax(weights) > 0 else 1.0
        sizes = 20 + 220 * (weights / denom)
        sc = plt.scatter(
            [z["lon"] for z in zones],
            [z["lat"] for z in zones],
            s=sizes,
            c=weights,
            cmap="YlOrRd",
            edgecolors="#111827",
            linewidths=0.3,
            alpha=0.85,
            zorder=3,
        )
        cb = plt.colorbar(sc)
        cb.set_label("Home weight")

    plt.xlim(minlon, maxlon)
    plt.ylim(minlat, maxlat)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Zone centroid map sized by home weight (grid overlay)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def main() -> None:
    bounds = parse_bounds_from_osm(OSM_PATH)
    roads = collect_highway_lines(OSM_PATH)
    zones = read_zones(ZONES_CSV)
    plot(OUT_PNG, roads, zones, bounds)
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()

