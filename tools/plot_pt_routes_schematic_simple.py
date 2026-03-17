#!/usr/bin/env python3
"""
Схематическая карта маршрутов ОТ по дорожной сети Shamalgan:
- каждый маршрут рисуется отдельным цветом,
- линии сдвинуты друг от друга, чтобы не накладываться.

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

try:
    from shapely.geometry import LineString
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
OUT_IMG = ROOT / "docs" / "ru" / "progress" / "img" / "pt_routes_schematic.png"

LINE_COLORS = {
    "line_6": "#1D4ED8",
    "line_11": "#15803D",
    "line_213": "#EA580C",
    "line_256": "#7E22CE",
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


def longest_connected_segment(pts: list, gap_threshold_m: float = 500.0) -> list:
    """Разбить ломаную по большим скачкам и вернуть самый длинный по числу точек отрезок."""
    if len(pts) < 2:
        return pts
    segments = []
    seg = [pts[0]]
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        if d > gap_threshold_m and len(seg) >= 2:
            segments.append(seg)
            seg = [b]
        else:
            seg.append(b)
    if seg:
        segments.append(seg)
    if not segments:
        return pts
    # Выбираем отрезок с максимальной протяжённостью (span), а не по числу точек — чтобы не взять петлю у остановки.
    def span(seg):
        xs = [p[0] for p in seg]
        ys = [p[1] for p in seg]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    return max(segments, key=span)


def offset_polyline(pts, offset_m: float):
    """
    Сдвигаем весь маршрут как жёсткое тело:
    - считаем усреднённое направление по первой и последней точке,
    - берём к нему перпендикуляр и сдвигаем на фиксированное расстояние.
    Так не возникает «завитушек» по ходу линии.
    """
    if len(pts) < 2 or offset_m == 0:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    dx = x1 - x0
    dy = y1 - y0
    seg_len = (dx**2 + dy**2) ** 0.5 or 1.0
    nx = -dy / seg_len
    ny = dx / seg_len
    xs_off = []
    ys_off = []
    for x, y in pts:
        xs_off.append(x + nx * offset_m)
        ys_off.append(y + ny * offset_m)
    return list(zip(xs_off, ys_off))


def offset_polyline_segment_normal(pts: list, offset_m: float) -> list:
    """
    Параллельный сдвиг по нормали к каждому сегменту: на поворотах линия не пересекает соседей.
    offset_m > 0 — сдвиг вправо от направления движения, < 0 — влево.
    """
    if len(pts) < 2 or offset_m == 0:
        return pts
    n = len(pts)
    out = []
    for i in range(n):
        if i == 0:
            dx = pts[1][0] - pts[0][0]
            dy = pts[1][1] - pts[0][1]
        elif i == n - 1:
            dx = pts[n - 1][0] - pts[n - 2][0]
            dy = pts[n - 1][1] - pts[n - 2][1]
        else:
            dx1 = pts[i][0] - pts[i - 1][0]
            dy1 = pts[i][1] - pts[i - 1][1]
            dx2 = pts[i + 1][0] - pts[i][0]
            dy2 = pts[i + 1][1] - pts[i][1]
            L1 = (dx1 * dx1 + dy1 * dy1) ** 0.5 or 1.0
            L2 = (dx2 * dx2 + dy2 * dy2) ** 0.5 or 1.0
            nx1, ny1 = dy1 / L1, -dx1 / L1
            nx2, ny2 = dy2 / L2, -dx2 / L2
            nx, ny = nx1 + nx2, ny1 + ny2
            ll = (nx * nx + ny * ny) ** 0.5
            if ll < 1e-9:
                nx, ny = nx1, ny1
            else:
                nx, ny = nx / ll, ny / ll
            out.append((pts[i][0] + nx * offset_m, pts[i][1] + ny * offset_m))
            continue
        L = (dx * dx + dy * dy) ** 0.5 or 1.0
        nx = dy / L
        ny = -dx / L
        out.append((pts[i][0] + nx * offset_m, pts[i][1] + ny * offset_m))
    return out


def trim_tail_outliers(pts: list, n_check: int = 5) -> list:
    """
    Удалить с конца точки-выбросы: если последняя точка ближе к началу маршрута,
    чем к предыдущей (петля/депо в данных), обрезаем.
    """
    if len(pts) <= n_check + 1:
        return pts
    while len(pts) >= 3:
        last = pts[-1]
        prev = pts[-2]
        first = pts[0]
        d_to_prev = (last[0] - prev[0]) ** 2 + (last[1] - prev[1]) ** 2
        d_to_first = (last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2
        if d_to_first < d_to_prev:
            pts = pts[:-1]
        else:
            break
    return pts


def truncate_by_x_max(pts: list, x_max: float) -> list:
    """Обрезать ломаную: удалить точки с X > x_max (выбросы справа)."""
    if not pts:
        return pts
    out = []
    for p in pts:
        if p[0] <= x_max:
            out.append(p)
        else:
            break
    return out if len(out) >= 2 else pts


def dedupe_consecutive(pts: list) -> list:
    """Удалить подряд идущие совпадающие точки (чистка для Shapely)."""
    if len(pts) < 2:
        return pts
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def drop_duplicates_keep_order(pts: list) -> list:
    """Удалить дубликаты, сохраняя порядок следования (как pandas drop_duplicates)."""
    if len(pts) < 2:
        return pts
    seen = set()
    out = []
    for p in pts:
        key = (round(p[0], 6), round(p[1], 6))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out if len(out) >= 2 else pts


def remove_last_if_outlier(pts: list, x_max: float, angle_deg_threshold: float = 90.0) -> list:
    """Удалить последнюю точку, если она восточнее x_max или резко меняет направление."""
    if len(pts) < 3:
        return pts
    while len(pts) >= 3:
        last = pts[-1]
        if last[0] > x_max:
            pts = pts[:-1]
            continue
        # Резкое изменение направления: угол между предпоследним и последним сегментом
        a, b, c = pts[-3], pts[-2], pts[-1]
        dx1, dy1 = b[0] - a[0], b[1] - a[1]
        dx2, dy2 = c[0] - b[0], c[1] - b[1]
        L1 = (dx1 * dx1 + dy1 * dy1) ** 0.5 or 1e-9
        L2 = (dx2 * dx2 + dy2 * dy2) ** 0.5 or 1e-9
        cos_a = (dx1 * dx2 + dy1 * dy2) / (L1 * L2)
        cos_a = max(-1.0, min(1.0, cos_a))
        angle_deg = np.degrees(np.arccos(cos_a))
        if angle_deg > angle_deg_threshold:
            pts = pts[:-1]
        else:
            break
    return pts


def offset_polyline_shapely(pts: list, offset_m: float, join_style: int = 2, mitre_limit: float = 1.0) -> list:
    """Параллельный сдвиг через Shapely. Рисуем ТОЛЬКО смещённую линию (не оригинал)."""
    if not HAS_SHAPELY or len(pts) < 2 or offset_m == 0:
        return pts
    ls = LineString(pts)
    try:
        side = "right" if offset_m > 0 else "left"
        geom = ls.parallel_offset(abs(offset_m), side=side, join_style=join_style, mitre_limit=mitre_limit)
    except Exception:
        return offset_polyline_segment_normal(pts, offset_m)
    if geom.is_empty:
        return offset_polyline_segment_normal(pts, offset_m)
    if geom.geom_type == "MultiLineString":
        geom = max(geom.geoms, key=lambda g: g.length)
    return list(geom.coords)


def truncate_polyline_at(pts: list, target_x: float, target_y: float) -> list:
    """Обрезать ломаную: оставить только до точки, ближайшей к (target_x, target_y)."""
    if len(pts) < 2:
        return pts
    best_i = 0
    best_d2 = (pts[0][0] - target_x) ** 2 + (pts[0][1] - target_y) ** 2
    for i in range(1, len(pts)):
        d2 = (pts[i][0] - target_x) ** 2 + (pts[i][1] - target_y) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_i = i
    return pts[: best_i + 1]


def truncate_polyline_ending_near(pts: list, target_x: float, target_y: float) -> list:
    """Обрезать так, чтобы маршрут был трассирован по всему пути и заканчивался у (target_x, target_y).
    Если ближайшая к цели вершина в начале ломаной — разворачиваем и обрезаем (показываем путь до цели)."""
    if len(pts) < 2:
        return pts
    best_i = 0
    best_d2 = (pts[0][0] - target_x) ** 2 + (pts[0][1] - target_y) ** 2
    for i in range(1, len(pts)):
        d2 = (pts[i][0] - target_x) ** 2 + (pts[i][1] - target_y) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_i = i
    # Ближайшая вершина в первой половине — маршрут в данных идёт от цели; показываем от другого конца до цели.
    if best_i < len(pts) // 2:
        pts = pts[::-1]
        pts = truncate_polyline_at(pts, target_x, target_y)
    else:
        pts = pts[: best_i + 1]
    return pts


# Целевые точки окончания маршрутов (по картинке 1: синий и зелёный кружки).
ROUTE_6_END_NEAR = (632200.0, 4804000.0)   # синий кружок
ROUTE_11_END_NEAR = (632900.0, 4803000.0)   # зелёный кружок
# Участок 11 слева от 213 не рисуем: обрезаем до точки у поворота 213 (начинаем справа от 213).
ROUTE_11_START_RIGHT_OF_213_NEAR = (632500.0, 4803800.0)
# Ограничение по X: выбросы справа от этой отметки удаляем.
ROUTE_11_X_MAX = 633500.0


def main():
    nodes, links = read_network(NETWORK)
    routes = read_schedule(SCHEDULE)
    if not routes:
        raise RuntimeError("No PT routes found in transitSchedule.xml")

    by_line: dict[str, list[tuple[str, list[str]]]] = {}
    for line_id, route_id, link_refs in routes:
        by_line.setdefault(line_id, []).append((route_id, link_refs))

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)

    # фон: вся сеть серым
    for l in links.values():
        fr = nodes.get(l["from"])
        to = nodes.get(l["to"])
        if not fr or not to:
            continue
        ax.plot([fr[0], to[0]], [fr[1], to[1]], color="#e5e7eb", linewidth=0.4, alpha=0.7)

    all_x, all_y = [], []

    # 6 и 11 по разные стороны от 213, равноудалённость 80 м.
    line_base_offset = {
        "line_6": -80.0,
        "line_11": 80.0,
        "line_213": 0.0,
        "line_256": 0.0,
    }

    for line_id, route_list in sorted(by_line.items()):
        base_color = LINE_COLORS.get(line_id, "#111827")
        base_off = line_base_offset.get(line_id, 0.0)

        # Одно направление на маршрут — без обратного хода.
        if not route_list:
            continue
        # Для маршрута 11 берём направление с максимальной протяжённостью и числом точек (весь путь).
        if line_id == "line_11" and len(route_list) >= 1:
            best_route = None
            best_span = -1
            best_npts = -1
            for rid, refs in route_list:
                p = build_polyline(refs, links, nodes)
                if len(p) < 2:
                    continue
                xs, ys = [q[0] for q in p], [q[1] for q in p]
                span = (max(xs) - min(xs)) + (max(ys) - min(ys))
                # выбираем по протяжённости, при равенстве — по числу точек
                if span > best_span or (span == best_span and len(p) > best_npts):
                    best_span = span
                    best_npts = len(p)
                    best_route = (rid, refs)
            if best_route is not None:
                route_id, link_refs = best_route
            else:
                route_id, link_refs = route_list[0]
        else:
            route_id, link_refs = route_list[0]

        pts = build_polyline(link_refs, links, nodes)
        if len(pts) < 2:
            continue
        # Маршрут 11: самый длинный связный отрезок и обрезка выбросов в конце (депо/петля).
        if line_id == "line_11":
            pts = longest_connected_segment(pts, gap_threshold_m=1500.0)
            pts = trim_tail_outliers(pts, n_check=5)
            # Убираем линию 11 слева от 213: рисуем только от точки у поворота 213 и дальше.
            best_i = min(
                range(len(pts)),
                key=lambda i: (pts[i][0] - ROUTE_11_START_RIGHT_OF_213_NEAR[0]) ** 2
                + (pts[i][1] - ROUTE_11_START_RIGHT_OF_213_NEAR[1]) ** 2,
            )
            pts = pts[best_i:]
            pts = truncate_by_x_max(pts, ROUTE_11_X_MAX)
            pts = dedupe_consecutive(pts)
            if len(pts) < 2:
                continue

        # Обрезаем только маршрут 6 у синего кружка. 213 и 256 не трогаем. 11 рисуем целиком, слева от 213.
        if line_id == "line_6":
            pts = truncate_polyline_at(pts, ROUTE_6_END_NEAR[0], ROUTE_6_END_NEAR[1])
            if len(pts) < 2:
                continue

        # 6 и 11: параллельный сдвиг по нормали к сегментам (на поворотах не пересекаются с 213).
        if line_id == "line_11" and base_off != 0 and HAS_SHAPELY:
            pts_off = offset_polyline_shapely(pts, base_off, join_style=2, mitre_limit=1.0)
        elif line_id in ("line_6", "line_11") and base_off != 0:
            pts_off = offset_polyline_segment_normal(pts, base_off)
        else:
            pts_off = offset_polyline(pts, base_off)
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

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    pad_x = (max_x - min_x) * 0.05
    pad_y = (max_y - min_y) * 0.05
    ax.set_xlim(min_x - pad_x, max_x + pad_x)
    ax.set_ylim(min_y - pad_y, max_y + pad_y)

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
