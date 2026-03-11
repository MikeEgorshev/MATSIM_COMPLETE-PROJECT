#!/usr/bin/env python3
"""
Build a compact PT network infographic and interpretation summary from MATSim inputs.

Inputs:
- scenarios/shamalgan/network-with-pt.xml
- scenarios/shamalgan/transitSchedule.xml

Outputs:
- analysis-artifacts/pt-data/pt_network_infographic.png
- analysis-artifacts/pt-data/pt_network_interpretation.md
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
OUT_IMG = ROOT / "Visualization" / "pt_network_infographic.png"
OUT_MD = ROOT / "Visualization" / "pt_network_interpretation.md"

LINE_COLORS = [
    "#0F766E",
    "#BE123C",
    "#1D4ED8",
    "#7E22CE",
    "#EA580C",
    "#15803D",
    "#1E3A8A",
    "#A21CAF",
]
ROUTE_SHIFT_X_M = 25.0
ROUTE_SHIFT_Y_M = 20.0


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


def read_network(path: Path):
    root = ET.parse(path).getroot()
    nodes = {}
    for node in root.findall("./nodes/node"):
        nodes[node.attrib["id"]] = (float(node.attrib["x"]), float(node.attrib["y"]))

    links = {}
    for link in root.findall("./links/link"):
        from_id = link.attrib["from"]
        to_id = link.attrib["to"]
        length = float(link.attrib.get("length", "0"))
        if length <= 0 and from_id in nodes and to_id in nodes:
            x1, y1 = nodes[from_id]
            x2, y2 = nodes[to_id]
            length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        links[link.attrib["id"]] = {
            "from": from_id,
            "to": to_id,
            "length": length,
        }
    return nodes, links


def read_schedule(path: Path):
    root = ET.parse(path).getroot()
    facilities = {}
    for stop in root.findall("./transitStops/stopFacility"):
        stop_id = stop.attrib["id"]
        base_area = stop.attrib.get("stopAreaId")
        if not base_area:
            base_area = stop_id.rsplit(".1", 1)[0] if stop_id.endswith(".1") else stop_id
        facilities[stop.attrib["id"]] = {
            "x": float(stop.attrib["x"]),
            "y": float(stop.attrib["y"]),
            "name": stop.attrib.get("name", ""),
            "linkRefId": stop.attrib.get("linkRefId", ""),
            "stopAreaId": base_area,
        }

    routes = []
    for line in root.findall("./transitLine"):
        line_id = line.attrib["id"]
        for route in line.findall("./transitRoute"):
            route_id = route.attrib["id"]

            stop_refs = []
            stop_offsets = []
            for stop in route.findall("./routeProfile/stop"):
                stop_refs.append(stop.attrib["refId"])
                stop_offsets.append(parse_time_to_sec(stop.attrib.get("departureOffset", "00:00:00")))

            link_refs = [x.attrib["refId"] for x in route.findall("./route/link")]
            departures = [
                parse_time_to_sec(dep.attrib["departureTime"])
                for dep in route.findall("./departures/departure")
            ]
            departures.sort()

            routes.append(
                {
                    "line_id": line_id,
                    "route_id": route_id,
                    "stop_refs": stop_refs,
                    "stop_offsets": stop_offsets,
                    "link_refs": link_refs,
                    "departures": departures,
                }
            )
    return facilities, routes


def build_route_polyline(link_refs, links, nodes):
    points = []
    missing = 0
    for ref in link_refs:
        link = links.get(ref)
        if not link:
            missing += 1
            continue
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            missing += 1
            continue
        if not points:
            points.extend([fr, to])
            continue
        if points[-1] != fr:
            points.append(fr)
        points.append(to)
    return points, missing


def median_headway_minutes(departures):
    if len(departures) < 2:
        return None
    gaps = [departures[i + 1] - departures[i] for i in range(len(departures) - 1)]
    return statistics.median(gaps) / 60.0


def main() -> None:
    nodes, links = read_network(NETWORK)
    facilities, routes = read_schedule(SCHEDULE)
    if not routes:
        raise RuntimeError("No transit routes found in schedule.")

    line_stats = {}
    line_hour_counts = defaultdict(Counter)
    total_hour_counts = Counter()
    missing_route_links = 0

    for route in routes:
        line_id = route["line_id"]
        route_id = route["route_id"]
        stop_refs = route["stop_refs"]
        departures = route["departures"]
        link_refs = route["link_refs"]

        polyline, miss = build_route_polyline(link_refs, links, nodes)
        missing_route_links += miss
        route["polyline"] = polyline

        route_len_m = sum(links[x]["length"] for x in link_refs if x in links)
        route["route_len_km"] = route_len_m / 1000.0

        stop_areas = []
        stop_coords = []
        for ref in stop_refs:
            if ref in facilities:
                info = facilities[ref]
                stop_areas.append(info["stopAreaId"])
                stop_coords.append((info["x"], info["y"]))
        route["stop_coords"] = stop_coords
        route["stop_areas"] = stop_areas

        headway_min = median_headway_minutes(departures)
        route["headway_min"] = headway_min
        route["span_first"] = departures[0] if departures else None
        route["span_last"] = departures[-1] if departures else None
        route["direction"] = "inbound" if route_id.endswith("_inbound") else "outbound"

        if line_id not in line_stats:
            line_stats[line_id] = {
                "routes": 0,
                "route_km": 0.0,
                "stop_areas": set(),
                "departures": 0,
                "first_dep": None,
                "last_dep": None,
                "headways": [],
                "route_ids": [],
            }

        stats = line_stats[line_id]
        stats["routes"] += 1
        stats["route_km"] += route["route_len_km"]
        stats["stop_areas"].update(stop_areas)
        stats["departures"] += len(departures)
        stats["route_ids"].append(route_id)
        if headway_min is not None:
            stats["headways"].append(headway_min)
        if departures:
            first_dep = departures[0]
            last_dep = departures[-1]
            stats["first_dep"] = first_dep if stats["first_dep"] is None else min(stats["first_dep"], first_dep)
            stats["last_dep"] = last_dep if stats["last_dep"] is None else max(stats["last_dep"], last_dep)

        for dep in departures:
            hour = dep // 3600
            line_hour_counts[line_id][hour] += 1
            total_hour_counts[hour] += 1

    line_ids = sorted(line_stats.keys(), key=line_sort_key)
    color_by_line = {line_id: LINE_COLORS[i % len(LINE_COLORS)] for i, line_id in enumerate(line_ids)}

    total_departures = sum(line_stats[x]["departures"] for x in line_ids)
    unique_stop_areas = set()
    for line_id in line_ids:
        unique_stop_areas.update(line_stats[line_id]["stop_areas"])

    all_first = [line_stats[x]["first_dep"] for x in line_ids if line_stats[x]["first_dep"] is not None]
    all_last = [line_stats[x]["last_dep"] for x in line_ids if line_stats[x]["last_dep"] is not None]
    global_first = min(all_first) if all_first else None
    global_last = max(all_last) if all_last else None

    fig = plt.figure(figsize=(18, 10), dpi=180)
    grid = fig.add_gridspec(2, 2, width_ratios=[2.35, 1.15], height_ratios=[1.0, 1.0], wspace=0.20, hspace=0.28)
    ax_map = fig.add_subplot(grid[:, 0])
    ax_hour = fig.add_subplot(grid[0, 1])
    ax_line = fig.add_subplot(grid[1, 1])

    for info in links.values():
        fr = nodes.get(info["from"])
        to = nodes.get(info["to"])
        if fr and to:
            ax_map.plot(
                [fr[0], to[0]],
                [fr[1], to[1]],
                color="#D1D5DB",
                linewidth=0.35,
                alpha=0.65,
                zorder=1,
            )

    line_rank = {line_id: idx for idx, line_id in enumerate(line_ids)}
    routes_sorted = sorted(routes, key=lambda r: (line_sort_key(r["line_id"]), r["route_id"]))

    for z, route in enumerate(routes_sorted, start=1):
        line_id = route["line_id"]
        color = color_by_line[line_id]
        poly = route["polyline"]
        dir_sign = -1.0 if route["direction"] == "inbound" else 1.0
        rank = line_rank[line_id]
        dx = ROUTE_SHIFT_X_M * dir_sign
        dy = (rank - (len(line_ids) - 1) / 2.0) * ROUTE_SHIFT_Y_M
        linestyle = "--" if route["direction"] == "inbound" else "-"
        if len(poly) >= 2:
            xs = [p[0] + dx for p in poly]
            ys = [p[1] + dy for p in poly]
            ax_map.plot(xs, ys, color=color, linewidth=2.0, alpha=0.92, linestyle=linestyle, zorder=2 + z * 0.01)
        if route["stop_coords"]:
            if route["direction"] == "outbound":
                sx = [p[0] + dx for p in route["stop_coords"]]
                sy = [p[1] + dy for p in route["stop_coords"]]
                ax_map.scatter(
                    sx,
                    sy,
                    s=12,
                    color=color,
                    edgecolors="#FFFFFF",
                    linewidths=0.35,
                    alpha=0.96,
                    zorder=4,
                )

    legend_handles = []
    for line_id in line_ids:
        stats = line_stats[line_id]
        label = (
            f"{line_id.replace('line_', '')}: "
            f"{len(stats['stop_areas'])} phys. stops, {stats['departures']} dep/day"
        )
        legend_handles.append(Line2D([0], [0], color=color_by_line[line_id], lw=3, label=label))
    legend_handles.append(Line2D([0], [0], color="#111827", lw=2, linestyle="-", label="outbound"))
    legend_handles.append(Line2D([0], [0], color="#111827", lw=2, linestyle="--", label="inbound"))
    ax_map.legend(handles=legend_handles, loc="upper left", fontsize=8, frameon=True)

    ax_map.set_aspect("equal", adjustable="box")
    ax_map.set_title("Route geometry on network-with-pt.xml", loc="left", fontsize=12, fontweight="bold")
    ax_map.set_xlabel("X (EPSG:32643)")
    ax_map.set_ylabel("Y (EPSG:32643)")
    ax_map.grid(alpha=0.12)

    if total_hour_counts:
        hour_min = min(total_hour_counts.keys())
        hour_max = max(total_hour_counts.keys())
        hours = list(range(hour_min, hour_max + 1))
        bottom = [0] * len(hours)
        for line_id in line_ids:
            vals = [line_hour_counts[line_id][h] for h in hours]
            ax_hour.bar(
                hours,
                vals,
                width=0.85,
                bottom=bottom,
                color=color_by_line[line_id],
                label=line_id.replace("line_", ""),
                alpha=0.95,
            )
            bottom = [bottom[i] + vals[i] for i in range(len(hours))]
        ax_hour.set_xticks(hours)
        ax_hour.set_title("Departures by hour (stacked by line)", loc="left", fontsize=11, fontweight="bold")
        ax_hour.set_xlabel("Hour of day")
        ax_hour.set_ylabel("Departures")
        ax_hour.grid(axis="y", alpha=0.20)
        ax_hour.legend(title="Line", fontsize=8, title_fontsize=8, ncol=2, loc="upper right")

    y_pos = list(range(len(line_ids)))
    line_km = [line_stats[x]["route_km"] for x in line_ids]
    line_labels = [x.replace("line_", "") for x in line_ids]
    colors = [color_by_line[x] for x in line_ids]
    ax_line.barh(y_pos, line_km, color=colors, alpha=0.95)
    ax_line.set_yticks(y_pos, line_labels)
    ax_line.invert_yaxis()
    ax_line.set_xlabel("Route length per loop [km]")
    ax_line.set_title("Line footprint + service level", loc="left", fontsize=11, fontweight="bold")
    ax_line.grid(axis="x", alpha=0.20)

    max_km = max(line_km) if line_km else 1.0
    ax_line.set_xlim(0, max_km * 2.05 if max_km > 0 else 1.0)
    for idx, line_id in enumerate(line_ids):
        stats = line_stats[line_id]
        dep_txt = stats["departures"]
        stop_txt = len(stats["stop_areas"])
        headway = statistics.median(stats["headways"]) if stats["headways"] else None
        head_txt = f"{headway:.1f} min" if headway is not None else "n/a"
        span_txt = "n/a"
        if stats["first_dep"] is not None and stats["last_dep"] is not None:
            span_txt = f"{sec_to_hhmm(stats['first_dep'])}-{sec_to_hhmm(stats['last_dep'])}"
        txt = f"{dep_txt} dep/day | {stop_txt} stops | headway~{head_txt} | {span_txt}"
        ax_line.text(line_km[idx] + max_km * 0.03, idx, txt, va="center", fontsize=8)

    top_text = (
        f"Shamalgan PT parse: {len(line_ids)} lines, {len(routes)} routes, "
        f"{len(unique_stop_areas)} physical stops, {total_departures} departures/day"
    )
    span_text = (
        f"Service window: {sec_to_hhmm(global_first)}-{sec_to_hhmm(global_last)}"
        if global_first is not None and global_last is not None
        else "Service window: n/a"
    )
    fig.suptitle(top_text, x=0.01, ha="left", y=0.985, fontsize=15, fontweight="bold")
    fig.text(0.01, 0.960, span_text, fontsize=10)
    fig.text(
        0.01,
        0.012,
        f"Sources: {SCHEDULE.relative_to(ROOT)} + {NETWORK.relative_to(ROOT)} | Generated {datetime.now():%Y-%m-%d %H:%M}",
        fontsize=8,
        color="#4B5563",
    )

    OUT_IMG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_IMG, bbox_inches="tight")
    plt.close(fig)

    lines = []
    lines.append("# PT Network Interpretation")
    lines.append("")
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}")
    lines.append("")
    lines.append("## High-level read")
    lines.append(f"- Lines: {len(line_ids)}")
    lines.append(f"- Routes: {len(routes)}")
    lines.append(f"- Physical stops (unique stopAreaId): {len(unique_stop_areas)}")
    lines.append(f"- Departures per day (from schedule): {total_departures}")
    if global_first is not None and global_last is not None:
        lines.append(f"- Service window: {sec_to_hhmm(global_first)} to {sec_to_hhmm(global_last)}")
    lines.append("")
    lines.append("## Line summary")
    lines.append("| Line | Routes | Physical stops | Loop km | Departures/day | Span | Median headway |")
    lines.append("|---|---:|---:|---:|---:|---|---:|")

    for line_id in line_ids:
        stats = line_stats[line_id]
        headway = statistics.median(stats["headways"]) if stats["headways"] else None
        head_txt = f"{headway:.1f} min" if headway is not None else "n/a"
        span_txt = "n/a"
        if stats["first_dep"] is not None and stats["last_dep"] is not None:
            span_txt = f"{sec_to_hhmm(stats['first_dep'])}-{sec_to_hhmm(stats['last_dep'])}"
        lines.append(
            "| "
            + f"{line_id.replace('line_', '')} | {stats['routes']} | {len(stats['stop_areas'])} | "
            + f"{stats['route_km']:.2f} | {stats['departures']} | {span_txt} | {head_txt} |"
        )

    lines.append("")
    lines.append("## Data-quality checks")
    lines.append(f"- Route link references missing in network: {missing_route_links}")
    lines.append("- Route lengths are computed from `route/linkRefId` lengths in `network-with-pt.xml`.")
    lines.append("- Physical stops are counted using `stopAreaId` to avoid platform duplicates.")
    lines.append("")
    lines.append(f"Infographic: `{OUT_IMG.relative_to(ROOT)}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved infographic: {OUT_IMG}")
    print(f"Saved interpretation: {OUT_MD}")
    print(top_text)
    if global_first is not None and global_last is not None:
        print(span_text)


if __name__ == "__main__":
    main()
