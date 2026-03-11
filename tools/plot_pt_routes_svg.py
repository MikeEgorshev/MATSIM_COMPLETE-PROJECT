#!/usr/bin/env python3
"""
Create a dependency-free SVG map of PT routes along the road network (link-based),
like SimWrapper Transit Viewer. Uses transitSchedule.xml route/link sequence and
network-with-pt.xml for geometry.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
OUT = ROOT / "Visualization" / "pt_routes_map.svg"

WIDTH = 1400
HEIGHT = 1000
PAD = 80
COLORS = [
    "#00695C",
    "#C62828",
    "#1565C0",
    "#6A1B9A",
    "#EF6C00",
    "#2E7D32",
    "#283593",
    "#AD1457",
]


def read_network(path: Path) -> tuple[dict[str, tuple[float, float]], dict[str, dict]]:
    tree = ET.parse(path)
    root = tree.getroot()
    nodes = {}
    for n in root.findall(".//node"):
        nid = n.attrib.get("id")
        if nid:
            nodes[nid] = (float(n.attrib["x"]), float(n.attrib["y"]))
    links = {}
    for link in root.findall(".//link"):
        lid = link.attrib.get("id")
        if not lid:
            continue
        fr = link.attrib.get("from")
        to = link.attrib.get("to")
        if fr and to:
            links[lid] = {"from": fr, "to": to}
    return nodes, links


def read_schedule(path: Path) -> tuple[dict, list]:
    tree = ET.parse(path)
    root = tree.getroot()
    facilities = {}
    for s in root.findall("./transitStops/stopFacility"):
        fid = s.attrib["id"]
        facilities[fid] = (float(s.attrib["x"]), float(s.attrib["y"]))

    routes = []
    for line in root.findall("./transitLine"):
        line_id = line.attrib["id"]
        for route in line.findall("./transitRoute"):
            route_id = route.attrib["id"]
            link_refs = [e.attrib["refId"] for e in route.findall("./route/link")]
            stop_ids = [st.attrib["refId"] for st in route.findall("./routeProfile/stop")]
            stop_coords = [facilities[sid] for sid in stop_ids if sid in facilities]
            if link_refs:
                routes.append((line_id, route_id, link_refs, stop_coords))
            elif len(stop_coords) >= 2:
                # fallback: no link sequence, use straight segments
                routes.append((line_id, route_id, None, stop_coords))
    return facilities, routes


def build_route_polyline(
    link_refs: list[str],
    links: dict,
    nodes: dict,
) -> list[tuple[float, float]]:
    points = []
    for ref in link_refs:
        link = links.get(ref)
        if not link:
            continue
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            continue
        if not points:
            points.extend([fr, to])
            continue
        if points[-1] != fr:
            points.append(fr)
        points.append(to)
    return points


def scale_xy(x, y, min_x, max_x, min_y, max_y):
    sx = PAD + (x - min_x) * (WIDTH - 2 * PAD) / max(1e-9, (max_x - min_x))
    sy = HEIGHT - PAD - (y - min_y) * (HEIGHT - 2 * PAD) / max(1e-9, (max_y - min_y))
    return sx, sy


def main():
    nodes, links = read_network(NETWORK)
    facilities, routes = read_schedule(SCHEDULE)
    if not routes:
        raise RuntimeError("No routes found in transitSchedule.xml")

    # Build polylines along links; collect all points for bbox
    all_x, all_y = [], []
    route_polylines = []
    for line_id, route_id, link_refs, stop_coords in routes:
        if link_refs:
            pts = build_route_polyline(link_refs, links, nodes)
            if pts:
                route_polylines.append((line_id, route_id, pts, stop_coords))
                for x, y in pts:
                    all_x.append(x)
                    all_y.append(y)
        else:
            route_polylines.append((line_id, route_id, stop_coords, stop_coords))
            for x, y in stop_coords:
                all_x.append(x)
                all_y.append(y)
        for x, y in stop_coords:
            all_x.append(x)
            all_y.append(y)

    if not all_x:
        raise RuntimeError("No route geometry to draw")
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    # Slight padding in CRS units
    dx = max(1e-9, max_x - min_x) * 0.05
    dy = max(1e-9, max_y - min_y) * 0.05
    min_x -= dx
    max_x += dx
    min_y -= dy
    max_y += dy

    # Road network: draw links that have at least one node in bbox (with margin)
    def in_bbox(x, y):
        return min_x <= x <= max_x and min_y <= y <= max_y
    road_segments = []
    for link in links.values():
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            continue
        if in_bbox(fr[0], fr[1]) or in_bbox(to[0], to[1]):
            road_segments.append((fr, to))

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">')
    lines.append('<rect width="100%" height="100%" fill="#f0f1f3"/>')
    lines.append(
        '<text x="40" y="42" font-family="Segoe UI, Arial, sans-serif" font-size="28" fill="#1f2937">'
        'Shamalgan PT Routes (on road network)</text>'
    )
    lines.append(
        '<text x="40" y="68" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#4b5563">'
        'Routes drawn along link sequence (SimWrapper-style)</text>'
    )

    # Background: road network in light grey
    for (x1, y1), (x2, y2) in road_segments:
        sx1, sy1 = scale_xy(x1, y1, min_x, max_x, min_y, max_y)
        sx2, sy2 = scale_xy(x2, y2, min_x, max_x, min_y, max_y)
        lines.append(f'<line x1="{sx1:.1f}" y1="{sy1:.1f}" x2="{sx2:.1f}" y2="{sy2:.1f}" '
                     'stroke="#c8ccd0" stroke-width="1.2" stroke-linecap="round"/>')

    # PT route polylines (along links)
    legend_y = 86
    for i, (line_id, route_id, pts, stop_coords) in enumerate(route_polylines):
        color = COLORS[i % len(COLORS)]
        if pts:
            scaled = []
            for x, y in pts:
                sx, sy = scale_xy(x, y, min_x, max_x, min_y, max_y)
                scaled.append(f"{sx:.1f},{sy:.1f}")
            pt_str = " ".join(scaled)
            lines.append(
                f'<polyline points="{pt_str}" fill="none" stroke="{color}" stroke-width="3" '
                'stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>'
            )
        for x, y in stop_coords:
            sx, sy = scale_xy(x, y, min_x, max_x, min_y, max_y)
            lines.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="3.3" fill="{color}" stroke="#ffffff" stroke-width="1"/>')

        lx = 40 + (i % 2) * 360
        ly = legend_y + (i // 2) * 24
        lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 24}" y2="{ly}" stroke="{color}" stroke-width="4" />')
        n_stops = len(stop_coords)
        lines.append(
            f'<text x="{lx + 32}" y="{ly + 4}" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#111827">'
            f'{line_id} / {route_id} ({n_stops} stops)</text>'
        )

    lines.append('</svg>')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {OUT}")
    print(f"Routes: {len(route_polylines)} (drawn along links)")


if __name__ == "__main__":
    main()
