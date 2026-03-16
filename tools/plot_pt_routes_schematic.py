#!/usr/bin/env python3
"""
Схематическая карта маршрутов ОТ по дорожной сети Shamalgan:
- каждый маршрут рисуется отдельным цветом,
- линии слегка сдвинуты друг от друга, чтобы не накладываться.

Вход:
- scenarios/shamalgan/network-with-pt.xml
- scenarios/shamalgan/transitSchedule.xml

Выход:
- docs/ru/progress/img/pt_routes_schematic.png
"""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
OUT_IMG = ROOT / "docs" / "ru" / "progress" / "img" / "pt_routes_schematic.png"

# Цвета по линиям (совпадают с инфографикой):
LINE_COLORS = {
    "line_6": "#1D4ED8",    # синий
    "line_11": "#15803D",   # зелёный
    "line_213": "#EA580C",  # оранжевый
    "line_256": "#7E22CE",  # фиолетовый
}


def read_network(path: Path):
    root = ET.parse(path).getroot()
    nodes = {}
    for node in root.findall("./nodes/node"):
        nodes[node.attrib["id"]] = (float(node.attrib["x"]), float(node.attrib["y"]))

    links = {}
    for link in root.findall("./links/link"):
        links[link.attrib["id"]] = {
            "from": link.attrib["from"],
            "to": link.attrib["to"],
        }
    return nodes, links


def read_schedule(path: Path):
    root = ET.parse(path).getroot()
    routes = []
    for line in root.findall("./transitLine"):
        line_id = line.attrib["id"]
        for route in line.findall("./transitRoute"):
            route_id = route.attrib["id"]
            link_refs = [e.attrib["refId"] for e in route.findall("./route/link")]
            if link_refs:
                routes.append((line_id, route_id, link_refs))
    return routes


def build_polyline(link_refs, links, nodes):
    pts = []
    for ref in link_refs:
        link = links.get(ref)
        if not link:
            continue
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            continue
        if not pts:
            pts.extend([fr, to])
            continue
        if pts[-1] != fr:
            pts.append(fr)
        pts.append(to)
    return pts


def offset_polyline(pts, offset_m: float):
    """Сдвинуть ломаную на фиксированное расстояние в локально перпендикулярном направлении."""
    if len(pts) < 2 or offset_m == 0:
        return pts
    xs = np.array([p[0] for p in pts], dtype=float)
    ys = np.array([p[1] for p in pts], dtype=float)
    dx = np.gradient(xs)
    dy = np.gradient(ys)
    seg_len = np.hypot(dx, dy) + 1e-9
    nx = -dy / seg_len
    ny = dx / seg_len
    xs_off = xs + nx * offset_m
    ys_off = ys + ny * offset_m
    return list(zip(xs_off.tolist(), ys_off.tolist()))


def main():
    nodes, links = read_network(NETWORK)
    routes = read_schedule(SCHEDULE)
    if not routes:
        raise RuntimeError("No PT routes found in transitSchedule.xml")

    # Группируем по линии, чтобы два направления одной линии сдвигать симметрично.
    by_line = {}
    for line_id, route_id, link_refs in routes:
        by_line.setdefault(line_id, []).append((route_id, link_refs))

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)

    # Фоном нарисуем дорожную сеть тонкими серыми линиями.
    for lid, l in links.items():
        fr = nodes.get(l["from"])
        to = nodes.get(l["to"])
        if not fr or not to:
            continue
        ax.plot([fr[0], to[0]], [fr[1], to[1]], color="#e5e7eb", linewidth=0.4, alpha=0.7)

    all_x, all_y = [], []

    for line_id, route_list in sorted(by_line.items()):
        base_color = LINE_COLORS.get(line_id, "#111827")
        # Предопределённые сдвиги для направлений (в метрах).
        offsets = [-20.0, 20.0, -40.0, 40.0]
        for idx, (route_id, link_refs) in enumerate(route_list):
            pts = build_polyline(link_refs, links, nodes)
            if len(pts) < 2:
                continue
            offset = offsets[idx] if idx < len(offsets) else 0.0
            pts_off = offset_polyline(pts, offset)
            xs = [p[0] for p in pts_off]
            ys = [p[1] for p in pts_off]
            all_x.extend(xs)
            all_y.extend(ys)
            ax.plot(xs, ys, color=base_color, linewidth=2.4, alpha=0.95, label=f"{line_id}:{route_id}")

    if not all_x:
        raise RuntimeError("No geometry drawn for PT routes.")

    ax.set_aspect("equal")
    ax.set_xlabel("X (EPSG:32643)")
    ax.set_ylabel("Y (EPSG:32643)")
    ax.set_title("Схематическая карта маршрутов ОТ — Шамалган", fontsize=11)

    # Небольшой отступ по краям.
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    pad_x = (max_x - min_x) * 0.05
    pad_y = (max_y - min_y) * 0.05
    ax.set_xlim(min_x - pad_x, max_x + pad_x)
    ax.set_ylim(min_y - pad_y, max_y + pad_y)

    # Легенда по линиям (сводим label'ы).
    handles, labels = ax.get_legend_handles_labels()
    by_prefix = {}
    for h, lab in zip(handles, labels):
        prefix = lab.split(":", 1)[0]
        if prefix not in by_prefix:
            by_prefix[prefix] = h
    legend_entries = []
    for line_id in sorted(by_prefix.keys()):
        num = line_id.replace("line_", "")
        legend_entries.append((by_prefix[line_id], f"Маршрут {num}"))
    if legend_entries:
        h_list, l_list = zip(*legend_entries)
        ax.legend(h_list, l_list, loc="lower right", fontsize=8, frameon=True)

    OUT_IMG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT_IMG, dpi=150)
    plt.close(fig)
    print(f"Saved schematic PT map: {OUT_IMG}")


if __name__ == "__main__":
    main()

