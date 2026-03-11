#!/usr/bin/env python3
"""
Build PT schedule-focused infographic from MATSim transitSchedule.xml.

Outputs:
- analysis-artifacts/pt-data/pt_schedule_infographic.png
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
OUT_IMG = ROOT / "Visualization" / "pt_schedule_infographic.png"

LINE_COLORS = [
    "#0F766E",
    "#BE123C",
    "#1D4ED8",
    "#7E22CE",
    "#EA580C",
    "#15803D",
]


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def parse_time_to_sec(value: str) -> int:
    h, m, s = [int(x) for x in value.strip().split(":")]
    return h * 3600 + m * 60 + s


def sec_to_hhmm(value: int) -> str:
    h = value // 3600
    m = (value % 3600) // 60
    return f"{h:02d}:{m:02d}"


def line_sort_key(line_id: str):
    tail = line_id.rsplit("_", 1)[-1]
    if tail.isdigit():
        return (0, int(tail))
    return (1, line_id)


@dataclass
class RouteStats:
    line_id: str
    route_id: str
    direction: str
    stop_count: int
    departures: list[int]
    link_refs: list[str]
    route_length_km: float


def parse_network_link_lengths(path: Path) -> dict[str, float]:
    root = ET.parse(path).getroot()
    nodes: dict[str, tuple[float, float]] = {}
    lengths: dict[str, float] = {}

    for node in root.iter():
        if local_name(node.tag) != "node":
            continue
        node_id = node.attrib.get("id")
        if not node_id:
            continue
        x = float(node.attrib.get("x", "0"))
        y = float(node.attrib.get("y", "0"))
        nodes[node_id] = (x, y)

    for link in root.iter():
        if local_name(link.tag) != "link":
            continue
        link_id = link.attrib.get("id")
        if not link_id:
            continue
        length = float(link.attrib.get("length", "0") or "0")
        if length <= 0:
            fr = link.attrib.get("from")
            to = link.attrib.get("to")
            if fr in nodes and to in nodes:
                x1, y1 = nodes[fr]
                x2, y2 = nodes[to]
                length = float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        lengths[link_id] = max(0.0, length)

    return lengths


def parse_schedule(path: Path, link_lengths_m: dict[str, float]) -> list[RouteStats]:
    root = ET.parse(path).getroot()
    out: list[RouteStats] = []

    for line in root.iter():
        if local_name(line.tag) != "transitLine":
            continue
        line_id = line.attrib.get("id", "")

        for route in list(line):
            if local_name(route.tag) != "transitRoute":
                continue

            route_id = route.attrib.get("id", "")
            direction = "inbound" if route_id.endswith("_inbound") else "outbound"

            stop_count = 0
            departures: list[int] = []
            link_refs: list[str] = []

            for child in list(route):
                name = local_name(child.tag)
                if name == "routeProfile":
                    stop_count = sum(1 for x in list(child) if local_name(x.tag) == "stop")
                elif name == "route":
                    for route_part in list(child):
                        part_name = local_name(route_part.tag)
                        if part_name in {"startLink", "link", "endLink"}:
                            ref = route_part.attrib.get("refId")
                            if ref:
                                link_refs.append(ref)
                elif name == "departures":
                    for dep in list(child):
                        if local_name(dep.tag) == "departure":
                            departures.append(parse_time_to_sec(dep.attrib["departureTime"]))

            departures.sort()
            route_length_m = sum(link_lengths_m.get(link_id, 0.0) for link_id in link_refs)
            out.append(RouteStats(line_id, route_id, direction, stop_count, departures, link_refs, route_length_m / 1000.0))

    out.sort(key=lambda r: (line_sort_key(r.line_id), r.route_id))
    return out


def build_infographic(routes: list[RouteStats], out_img: Path) -> None:
    line_ids = sorted({r.line_id for r in routes}, key=line_sort_key)
    color_by_line = {line_id: LINE_COLORS[i % len(LINE_COLORS)] for i, line_id in enumerate(line_ids)}

    all_departures = [d for r in routes for d in r.departures]
    if not all_departures:
        raise RuntimeError("No departures found in transitSchedule.xml")

    hour_min = min(all_departures) // 3600
    hour_max = max(all_departures) // 3600
    hours = list(range(hour_min, hour_max + 1))
    hour_to_col = {h: i for i, h in enumerate(hours)}

    route_labels = []
    heat = np.zeros((len(routes), len(hours)), dtype=int)
    avg_headway = []
    min_headway = []
    max_headway = []
    first_last = []

    for row, route in enumerate(routes):
        line_short = route.line_id.replace("line_", "")
        dir_short = "in" if route.direction == "inbound" else "out"
        route_labels.append(f"{line_short}:{dir_short}")

        for dep in route.departures:
            h = dep // 3600
            heat[row, hour_to_col[h]] += 1

        if len(route.departures) >= 2:
            headways = [route.departures[i + 1] - route.departures[i] for i in range(len(route.departures) - 1)]
            avg_headway.append(sum(headways) / len(headways))
            min_headway.append(min(headways))
            max_headway.append(max(headways))
        else:
            avg_headway.append(0.0)
            min_headway.append(0.0)
            max_headway.append(0.0)

        first_last.append(
            (
                route.departures[0],
                route.departures[-1],
                len(route.departures),
                route.stop_count,
                route.route_length_km,
            )
        )

    fig = plt.figure(figsize=(18, 10), dpi=180)
    grid = fig.add_gridspec(2, 2, width_ratios=[2.2, 1.1], height_ratios=[1.2, 1.0], wspace=0.22, hspace=0.24)
    ax_timeline = fig.add_subplot(grid[0, 0])
    ax_heat = fig.add_subplot(grid[1, 0])
    ax_headway = fig.add_subplot(grid[0, 1])
    ax_text = fig.add_subplot(grid[1, 1])

    for y, route in enumerate(routes):
        x = [d / 3600.0 for d in route.departures]
        c = color_by_line[route.line_id]
        ax_timeline.scatter(x, [y] * len(x), s=8, color=c, alpha=0.9)
    ax_timeline.set_yticks(range(len(route_labels)))
    ax_timeline.set_yticklabels(route_labels, fontsize=8)
    ax_timeline.set_xlabel("Hour of day")
    ax_timeline.set_title("Departure timeline by route variant", loc="left", fontsize=12, fontweight="bold")
    ax_timeline.grid(alpha=0.2)

    im = ax_heat.imshow(heat, cmap="YlGnBu", aspect="auto")
    ax_heat.set_xticks(range(len(hours)))
    ax_heat.set_xticklabels([str(h) for h in hours], fontsize=8)
    ax_heat.set_yticks(range(len(route_labels)))
    ax_heat.set_yticklabels(route_labels, fontsize=8)
    ax_heat.set_xlabel("Hour of day")
    ax_heat.set_title("Departures per hour (route x hour heatmap)", loc="left", fontsize=12, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax_heat, fraction=0.02, pad=0.01)
    cbar.set_label("Departures/hour", fontsize=8)

    x_pos = np.arange(len(route_labels))
    avg_min = np.array(avg_headway) / 60.0
    low = np.maximum(avg_min - (np.array(min_headway) / 60.0), 0.0)
    high = np.maximum((np.array(max_headway) / 60.0) - avg_min, 0.0)
    colors = [color_by_line[r.line_id] for r in routes]
    ax_headway.bar(x_pos, avg_min, color=colors, alpha=0.9)
    ax_headway.errorbar(x_pos, avg_min, yerr=[low, high], fmt="none", ecolor="#111827", elinewidth=1.0, capsize=3)
    ax_headway.set_xticks(x_pos)
    ax_headway.set_xticklabels(route_labels, rotation=45, ha="right", fontsize=8)
    ax_headway.set_ylabel("Headway [min]")
    ax_headway.set_title("Headway profile (avg with min-max range)", loc="left", fontsize=12, fontweight="bold")
    ax_headway.grid(axis="y", alpha=0.2)

    line_dep = Counter()
    for route in routes:
        line_dep[route.line_id.replace("line_", "")] += len(route.departures)

    ax_text.axis("off")
    lines = [
        "Schedule Summary",
        f"Routes: {len(routes)}",
        f"Service window: {sec_to_hhmm(min(all_departures))}-{sec_to_hhmm(max(all_departures))}",
        f"Total departures/day: {sum(len(r.departures) for r in routes)}",
        "",
        "Departures by line:",
    ]
    for line_id in sorted(line_dep.keys(), key=lambda x: int(x) if x.isdigit() else 10**9):
        lines.append(f"- {line_id}: {line_dep[line_id]}")
    lines.append("")
    lines.append("Route details:")
    for lbl, (first, last, deps, stops, length_km) in zip(route_labels, first_last):
        lines.append(
            f"- {lbl}: {deps} dep | {stops} stops | {length_km:.2f} km | "
            f"{sec_to_hhmm(first)}-{sec_to_hhmm(last)}"
        )
    ax_text.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=9, family="monospace")

    fig.suptitle("Shamalgan PT schedule infographic", x=0.01, ha="left", fontsize=18, fontweight="bold")
    fig.text(
        0.01,
        0.02,
        "Source: scenarios/shamalgan/transitSchedule.xml + scenarios/shamalgan/network-with-pt.xml",
        fontsize=8,
        color="#4B5563",
    )

    out_img.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_img, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    link_lengths_m = parse_network_link_lengths(NETWORK)
    routes = parse_schedule(SCHEDULE, link_lengths_m)
    build_infographic(routes, OUT_IMG)
    print(f"Saved schedule infographic: {OUT_IMG.resolve()}")


if __name__ == "__main__":
    main()
