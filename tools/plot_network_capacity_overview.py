#!/usr/bin/env python3
"""
Create a capacity overview map for the Shamalgan road network.
Links are colored by capacity (veh/h). Same style as network_speed_overview.

Input: scenarios/shamalgan/network.xml
Output: Visualization/network-qc/network_capacity_overview.png
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
OUT = ROOT / "Visualization" / "network-qc" / "network_capacity_overview.png"


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
        cap = float(l.attrib.get("capacity", "0"))
        links.append((fr, to, cap))
    return links


def capacity_style(cap: float):
    """Color by capacity (veh/h): low=blue, high=red."""
    if cap >= 2000:
        return "#b2182b", 1.0   # dark red
    if cap >= 1000:
        return "#ef8a62", 0.9   # orange
    if cap >= 500:
        return "#67a9cf", 0.8   # light blue
    return "#2166ac", 0.65      # dark blue


def main() -> None:
    links = read_network(NETWORK)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f7f7f7")

    for fr, to, cap in links:
        color, alpha = capacity_style(cap)
        ax.plot([fr[0], to[0]], [fr[1], to[1]], color=color, alpha=alpha, linewidth=0.85)

    capacities = [c for _, _, c in links]
    p50 = sorted(capacities)[len(capacities) // 2] if capacities else 0
    title = "Shamalgan Road Network: Capacity Overview"
    subtitle = f"Links: {len(links):,} | Median capacity: {p50:.0f} veh/h"
    ax.set_title(f"{title}\n{subtitle}", fontsize=13)
    ax.set_xlabel("X (EPSG:32643)")
    ax.set_ylabel("Y (EPSG:32643)")
    ax.grid(alpha=0.15, linewidth=0.4)

    legend_handles = [
        Line2D([0], [0], color="#2166ac", lw=2, label="<500 veh/h"),
        Line2D([0], [0], color="#67a9cf", lw=2, label="500-1000 veh/h"),
        Line2D([0], [0], color="#ef8a62", lw=2, label="1000-2000 veh/h"),
        Line2D([0], [0], color="#b2182b", lw=2, label=">=2000 veh/h"),
    ]
    ax.legend(handles=legend_handles, loc="lower left")

    plt.tight_layout()
    plt.savefig(OUT, dpi=220)
    plt.close()

    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
