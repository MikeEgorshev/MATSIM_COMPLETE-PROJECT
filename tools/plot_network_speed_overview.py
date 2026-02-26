#!/usr/bin/env python3
"""
Create a free-speed overview map for the Shamalgan road network.

Input:
- scenarios/shamalgan/network.xml

Output:
- analysis-artifacts/network-qc/network_speed_overview.png
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network.xml"
OUT = ROOT / "analysis-artifacts" / "network-qc" / "network_speed_overview.png"


def read_network(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    nodes = {}
    for n in root.findall(".//node"):
        nodes[n.attrib["id"]] = (float(n.attrib["x"]), float(n.attrib["y"]))

    links = []
    for l in root.findall(".//link"):
        fr = nodes.get(l.attrib["from"])
        to = nodes.get(l.attrib["to"])
        if not fr or not to:
            continue
        fs_ms = float(l.attrib.get("freespeed", "0"))
        fs_kmh = fs_ms * 3.6
        links.append((fr, to, fs_kmh))
    return links


def speed_style(speed_kmh: float):
    if speed_kmh >= 60:
        return "#b2182b", 1.0
    if speed_kmh >= 40:
        return "#ef8a62", 0.9
    if speed_kmh >= 25:
        return "#67a9cf", 0.8
    return "#2166ac", 0.65


def main() -> None:
    links = read_network(NETWORK)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f7f7f7")

    for fr, to, speed_kmh in links:
        color, alpha = speed_style(speed_kmh)
        ax.plot([fr[0], to[0]], [fr[1], to[1]], color=color, alpha=alpha, linewidth=0.85)

    speeds = [s for _, _, s in links]
    p50 = sorted(speeds)[len(speeds) // 2] if speeds else 0
    title = "Shamalgan Road Network: Free-Speed Overview"
    subtitle = f"Links: {len(links):,} | Median free speed: {p50:.1f} km/h"
    ax.set_title(f"{title}\n{subtitle}", fontsize=13)
    ax.set_xlabel("X (EPSG:32643)")
    ax.set_ylabel("Y (EPSG:32643)")
    ax.grid(alpha=0.15, linewidth=0.4)

    legend_handles = [
        Line2D([0], [0], color="#2166ac", lw=2, label="<25 km/h"),
        Line2D([0], [0], color="#67a9cf", lw=2, label="25-40 km/h"),
        Line2D([0], [0], color="#ef8a62", lw=2, label="40-60 km/h"),
        Line2D([0], [0], color="#b2182b", lw=2, label=">=60 km/h"),
    ]
    ax.legend(handles=legend_handles, loc="lower left")

    plt.tight_layout()
    plt.savefig(OUT, dpi=220)
    plt.close()

    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
