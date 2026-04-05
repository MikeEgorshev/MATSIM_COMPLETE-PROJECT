#!/usr/bin/env python3
"""
Карта: узлы OSM со светофорами (highway=traffic_signals, crossing=traffic_signals)
поверх car-линков MATSim в EPSG:32643.

По умолчанию сохраняет три PNG рядом с --out:
  - обзор (полная сеть);
  - зум по bbox вокруг всех светофоров/crossing;
  - обзор + «лупа» (inset с mark_inset).

Пример:
  python tools/plot_traffic_signals_map.py
  python tools/plot_traffic_signals_map.py --out Visualization/network-qc/traffic_signals_map.png --no-inset
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

try:
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
except ImportError as e:  # pragma: no cover
    raise SystemExit("Нужен matplotlib с mpl_toolkits.axes_grid1") from e

try:
    from pyproj import Transformer
except ImportError as e:  # pragma: no cover
    raise SystemExit("Нужен пакет pyproj: pip install pyproj") from e

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OSM = ROOT / "original-input-data" / "shamalgan" / "map"
DEFAULT_NETWORK = ROOT / "scenarios" / "shamalgan" / "network.xml"
DEFAULT_OUT = ROOT / "Visualization" / "network-qc" / "traffic_signals_map.png"
TARGET_CRS = "EPSG:32643"


def _parse_modes(raw: str) -> set[str]:
    return {p.strip() for p in raw.replace(" ", "").split(",") if p.strip()}


def read_car_links(path: Path) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    tree = ET.parse(path)
    root = tree.getroot()
    nodes: dict[str, tuple[float, float]] = {}
    for n in root.findall(".//node"):
        nodes[n.attrib["id"]] = (float(n.attrib["x"]), float(n.attrib["y"]))
    out: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for l in root.findall(".//link"):
        if "car" not in _parse_modes(l.attrib.get("modes", "car")):
            continue
        fr = nodes.get(l.attrib["from"])
        to = nodes.get(l.attrib["to"])
        if fr and to:
            out.append((fr, to))
    return out


def _read_node_tags(node_el: ET.Element) -> dict[str, str]:
    return {t.attrib["k"]: t.attrib["v"] for t in node_el.findall("tag")}


def read_osm_traffic_signals(
    osm_path: Path, transformer: Transformer
) -> tuple[list[tuple[float, float, str]], list[tuple[float, float, str]]]:
    """
    Returns (highway_traffic_signals, crossing_traffic_signals) as (x, y, osm_node_id).
    """
    tree = ET.parse(osm_path)
    root = tree.getroot()
    highway_pts: list[tuple[float, float, str]] = []
    crossing_pts: list[tuple[float, float, str]] = []

    for node in root.findall("node"):
        lat_s = node.attrib.get("lat")
        lon_s = node.attrib.get("lon")
        if not lat_s or not lon_s:
            continue
        try:
            lat = float(lat_s)
            lon = float(lon_s)
        except ValueError:
            continue
        tags = _read_node_tags(node)
        nid = node.attrib.get("id", "")
        if tags.get("highway") == "traffic_signals":
            x, y = transformer.transform(lon, lat)
            highway_pts.append((x, y, nid))
        elif tags.get("crossing") == "traffic_signals":
            x, y = transformer.transform(lon, lat)
            crossing_pts.append((x, y, nid))

    return highway_pts, crossing_pts


def bbox_around_signals(
    all_pts: list[tuple[float, float, str]], *, pad_ratio: float = 0.38, min_pad_m: float = 180.0
) -> tuple[float, float, float, float]:
    """Возвращает (xmin, xmax, ymin, ymax) с полями вокруг всех точек."""
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    w = max(maxx - minx, 1.0)
    h = max(maxy - miny, 1.0)
    px = max(w * pad_ratio, min_pad_m)
    py = max(h * pad_ratio, min_pad_m)
    return minx - px, maxx + px, miny - py, maxy + py


def draw_network_and_signals(
    ax: plt.Axes,
    links: list[tuple[tuple[float, float], tuple[float, float]]],
    highway_pts: list[tuple[float, float, str]],
    crossing_pts: list[tuple[float, float, str]],
    *,
    link_lw: float = 0.55,
    link_alpha: float = 0.75,
    h_size: float = 120,
    c_size: float = 100,
) -> None:
    ax.set_facecolor("#e8eaed")
    for fr, to in links:
        ax.plot(
            [fr[0], to[0]],
            [fr[1], to[1]],
            color="#9aa0a6",
            alpha=link_alpha,
            linewidth=link_lw,
            zorder=1,
        )
    if highway_pts:
        hx = [p[0] for p in highway_pts]
        hy = [p[1] for p in highway_pts]
        ax.scatter(
            hx,
            hy,
            s=h_size,
            c="#c62828",
            marker="o",
            edgecolors="#1a1a1a",
            linewidths=0.8,
            zorder=4,
            label=f"highway=traffic_signals ({len(highway_pts)})",
        )
    if crossing_pts:
        cx = [p[0] for p in crossing_pts]
        cy = [p[1] for p in crossing_pts]
        ax.scatter(
            cx,
            cy,
            s=c_size,
            c="#ff9800",
            marker="s",
            edgecolors="#1a1a1a",
            linewidths=0.6,
            zorder=3,
            label=f"crossing=traffic_signals ({len(crossing_pts)})",
        )


def save_figure_overview(
    path: Path,
    links: list,
    highway_pts: list,
    crossing_pts: list,
    *,
    title: str,
    subtitle: str,
    dpi: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13, 9.5))
    ax = fig.add_subplot(111)
    draw_network_and_signals(ax, links, highway_pts, crossing_pts)
    ax.set_title(f"{title}\n{subtitle}", fontsize=11)
    ax.set_xlabel("X, м (EPSG:32643)")
    ax.set_ylabel("Y, м (EPSG:32643)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def save_figure_zoom(
    path: Path,
    links: list,
    highway_pts: list,
    crossing_pts: list,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    *,
    title: str,
    subtitle: str,
    dpi: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(11, 9))
    ax = fig.add_subplot(111)
    draw_network_and_signals(
        ax,
        links,
        highway_pts,
        crossing_pts,
        link_lw=0.9,
        h_size=220,
        c_size=190,
    )
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title(f"{title} (зум)\n{subtitle}", fontsize=11)
    ax.set_xlabel("X, м (EPSG:32643)")
    ax.set_ylabel("Y, м (EPSG:32643)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.92)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def save_figure_inset(
    path: Path,
    links: list,
    highway_pts: list,
    crossing_pts: list,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    *,
    title: str,
    subtitle: str,
    dpi: int,
) -> None:
    """Обзор + увеличенный фрагмент (лупа) сверху по центру (без наложения на оси основной карты)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111)
    draw_network_and_signals(ax, links, highway_pts, crossing_pts)
    ax.set_title(f"{title} + увеличение\n{subtitle}", fontsize=11)
    ax.set_xlabel("X, м (EPSG:32643)")
    ax.set_ylabel("Y, м (EPSG:32643)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)

    rect = Rectangle(
        (x0, y0),
        x1 - x0,
        y1 - y0,
        fill=False,
        edgecolor="#c62828",
        linewidth=1.4,
        linestyle="--",
        zorder=5,
    )
    ax.add_patch(rect)

    # Вставка: верхний центр осей (якорь — верхний центр окна зума), чтобы подписи не наезжали на Y слева
    axins = inset_axes(
        ax,
        width=3.4,
        height=3.4,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        bbox_transform=ax.transAxes,
        borderpad=0,
    )
    draw_network_and_signals(axins, links, highway_pts, crossing_pts, link_lw=1.0, h_size=200, c_size=170)
    axins.set_xlim(x0, x1)
    axins.set_ylim(y0, y1)
    axins.set_aspect("equal", adjustable="box")
    axins.grid(True, alpha=0.35, linestyle="--", linewidth=0.45)
    axins.set_title("Увеличение", fontsize=9, pad=4)
    axins.tick_params(axis="both", labelsize=7, pad=2)

    # Линии от нижних углов «лупы» к рамке на основной карте (зум снизу от вставки)
    mark_inset(ax, axins, loc1=3, loc2=4, fc="none", ec="0.35", lw=0.9)

    h1, l1 = ax.get_legend_handles_labels()
    # Легенда внизу справа — не пересекается с лупой сверху по центру
    ax.legend(h1, l1, loc="lower right", fontsize=9, framealpha=0.92)
    # tight_layout конфликтует с inset_axes; ручные поля стабильнее для «лупы»
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.08, top=0.90)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Карта светофоров OSM + сеть MATSim (обзор / зум / лупа).")
    ap.add_argument("--osm", type=Path, default=DEFAULT_OSM, help="OSM XML (node lat/lon)")
    ap.add_argument("--network", type=Path, default=DEFAULT_NETWORK, help="network.xml для фона")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="PNG: полный обзор")
    ap.add_argument(
        "--out-zoom",
        type=Path,
        default=None,
        help="PNG: зум (по умолчанию <stem>_zoom.png рядом с --out)",
    )
    ap.add_argument(
        "--out-inset",
        type=Path,
        default=None,
        help="PNG: обзор + лупа (по умолчанию <stem>_inset.png рядом с --out)",
    )
    ap.add_argument("--no-zoom", action="store_true", help="Не сохранять отдельный зум")
    ap.add_argument("--no-inset", action="store_true", help="Не сохранять вариант с лупой")
    ap.add_argument("--dpi", type=int, default=220)
    args = ap.parse_args()

    if not args.osm.is_file():
        raise SystemExit(f"OSM не найден: {args.osm}")
    if not args.network.is_file():
        raise SystemExit(f"Сеть не найдена: {args.network}")

    out_zoom = args.out_zoom
    if out_zoom is None:
        out_zoom = args.out.parent / f"{args.out.stem}_zoom{args.out.suffix}"
    out_inset = args.out_inset
    if out_inset is None:
        out_inset = args.out.parent / f"{args.out.stem}_inset{args.out.suffix}"

    tx = Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True)
    highway_pts, crossing_pts = read_osm_traffic_signals(args.osm, tx)
    all_pts = highway_pts + crossing_pts
    if not all_pts:
        raise SystemExit("В OSM не найдено узлов traffic_signals (проверьте файл).")

    links = read_car_links(args.network)
    if not links:
        raise SystemExit("Нет car-линков в сети.")

    x0, x1, y0, y1 = bbox_around_signals(all_pts)
    title = "Шамалган — светофоры (OSM) на фоне car-сети MATSim"
    subtitle = (
        f"OSM: {args.osm.name} | сеть: {args.network.name} | всего точек: {len(all_pts)} | car-линков: {len(links):,}"
    )

    save_figure_overview(args.out, links, highway_pts, crossing_pts, title=title, subtitle=subtitle, dpi=args.dpi)
    print(f"Saved (обзор): {args.out.resolve()}")

    if not args.no_zoom:
        save_figure_zoom(
            out_zoom, links, highway_pts, crossing_pts, x0, x1, y0, y1, title=title, subtitle=subtitle, dpi=args.dpi
        )
        print(f"Saved (зум):   {out_zoom.resolve()}")

    if not args.no_inset:
        save_figure_inset(
            out_inset, links, highway_pts, crossing_pts, x0, x1, y0, y1, title=title, subtitle=subtitle, dpi=args.dpi
        )
        print(f"Saved (лупа):  {out_inset.resolve()}")


if __name__ == "__main__":
    main()
