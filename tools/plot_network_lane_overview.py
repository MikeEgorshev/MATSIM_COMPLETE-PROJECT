#!/usr/bin/env python3
"""
Create a lane-count overview map for the Shamalgan road network.

Input:
- scenarios/shamalgan/network.xml

Output:
- analysis-artifacts/network-qc/network_lane_overview.png
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network.xml"
OUT = ROOT / "analysis-artifacts" / "network-qc" / "network_lane_overview.png"


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
        lanes = float(l.attrib.get("permlanes", "1"))
        links.append((fr, to, lanes))
    return links


def lane_style(lanes: float):
    if lanes >= 2.0:
        return "#cc3311", 0.95, 1.15  # red, stronger
    return "#1f78b4", 0.45, 0.80  # blue, thinner


def main() -> None:
    links = read_network(NETWORK)
    lane_counts = Counter(int(round(lanes)) for _, _, lanes in links)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f6f7f9")

    for fr, to, lanes in links:
        color, alpha, width = lane_style(lanes)
        ax.plot([fr[0], to[0]], [fr[1], to[1]], color=color, alpha=alpha, linewidth=width)

    title = "Shamalgan Road Network: Link Lane Overview"
    subtitle = (
        f"Links: {len(links):,} | "
        + " | ".join(f"{k} lane: {v:,}" for k, v in sorted(lane_counts.items()))
    )
    ax.set_title(f"{title}\n{subtitle}", fontsize=13)
    ax.set_xlabel("X (EPSG:32643)")
    ax.set_ylabel("Y (EPSG:32643)")
    ax.grid(alpha=0.15, linewidth=0.4)

    legend_handles = [
        Line2D([0], [0], color="#1f78b4", lw=2, label="1 lane per link"),
        Line2D([0], [0], color="#cc3311", lw=2, label="2+ lanes per link"),
    ]
    ax.legend(handles=legend_handles, loc="lower left")

    plt.tight_layout()
    plt.savefig(OUT, dpi=220)
    plt.close()

    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
