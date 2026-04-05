#!/usr/bin/env python3
"""
Визуализация линков MATSim с раскраской по числу полос (атрибут permlanes на направленном линке).

Полезно для аудита: узкие грунтовки в селе часто остаются с permlanes=1 на каждый линк
(двусторонняя «одна полоса на два направления» в жизни vs две направленные полосы в модели).

Вход:  scenarios/shamalgan/network.xml (или --network)
Выход: Visualization/network-qc/network_lane_overview.png (или --out)

Пример:
  python tools/plot_network_lane_overview.py
  python tools/plot_network_lane_overview.py --network scenarios/shamalgan/network-with-pt.xml --modes car
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = ROOT / "scenarios" / "shamalgan" / "network.xml"
DEFAULT_OUT = ROOT / "Visualization" / "network-qc" / "network_lane_overview.png"

# Дискретные корзины permlanes (значение с линка MATSim)
LANE_BUCKETS = (
    # (верхняя граница exclusive, цвет, толщина линии, подпись легенды)
    (0.75, "#7b3294", 0.9, "<1 полосы (дробное permlanes)"),
    (1.5, "#2166ac", 0.75, "1 полоса"),
    (2.5, "#2ca25f", 0.95, "2 полосы"),
    (3.5, "#ff7f00", 1.1, "3 полосы"),
    (float("inf"), "#b2182b", 1.35, "4+ полос"),
)


def _parse_modes(raw: str) -> set[str]:
    return {p.strip() for p in raw.replace(" ", "").split(",") if p.strip()}


def read_network(path: Path, *, modes_filter: str | None) -> list[tuple[tuple[float, float], tuple[float, float], float]]:
    tree = ET.parse(path)
    root = tree.getroot()
    nodes: dict[str, tuple[float, float]] = {}
    for n in root.findall(".//node"):
        nodes[n.attrib["id"]] = (float(n.attrib["x"]), float(n.attrib["y"]))

    links: list[tuple[tuple[float, float], tuple[float, float], float]] = []
    for l in root.findall(".//link"):
        modes_attr = l.attrib.get("modes", "car")
        if modes_filter is not None and modes_filter not in _parse_modes(modes_attr):
            continue
        fr = nodes.get(l.attrib["from"])
        to = nodes.get(l.attrib["to"])
        if not fr or not to:
            continue
        raw = l.attrib.get("permlanes") or l.attrib.get("numberOfLanes") or "1"
        try:
            lanes = float(raw)
        except ValueError:
            lanes = 1.0
        links.append((fr, to, lanes))
    return links


def lane_style(lanes: float) -> tuple[str, float, float, str]:
    for hi, color, lw, label in LANE_BUCKETS:
        if lanes < hi:
            return color, 0.88, lw, label
    return LANE_BUCKETS[-1][1], 0.88, LANE_BUCKETS[-1][2], LANE_BUCKETS[-1][3]


def bucket_key(lanes: float) -> str:
    _, _, _, label = lane_style(lanes)
    return label


def main() -> None:
    ap = argparse.ArgumentParser(description="Карта линков сети MATSim по permlanes.")
    ap.add_argument("--network", type=Path, default=DEFAULT_NETWORK, help="Путь к network.xml")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="PNG выход")
    ap.add_argument(
        "--modes",
        default="car",
        help='Учитывать только линки, где в modes есть это значение (например car). Пустая строка — все линки.',
    )
    ap.add_argument("--dpi", type=int, default=220)
    args = ap.parse_args()

    modes_filter = args.modes.strip() if args.modes else None
    links = read_network(args.network, modes_filter=modes_filter)
    if not links:
        raise SystemExit("Нет линков для отрисовки (проверьте путь и фильтр --modes).")

    by_bucket = Counter(bucket_key(ln) for *_, ln in links)
    # Порядок легенды как в LANE_BUCKETS
    legend_order = [b[3] for b in LANE_BUCKETS]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(13, 9.5))
    ax = fig.add_subplot(111)
    ax.set_facecolor("#f0f1f3")

    for fr, to, lanes in links:
        color, alpha, width, _ = lane_style(lanes)
        ax.plot([fr[0], to[0]], [fr[1], to[1]], color=color, alpha=alpha, linewidth=width)

    counts_str = " | ".join(f"{k}: {by_bucket.get(k, 0):,}" for k in legend_order)
    title = "Шамалган — полосность направленных линков (MATSim permlanes)"
    subtitle = f"Файл: {args.network.name} | Линков: {len(links):,}\n{counts_str}"
    ax.set_title(f"{title}\n{subtitle}", fontsize=11)
    ax.set_xlabel("X, м (EPSG:32643)")
    ax.set_ylabel("Y, м (EPSG:32643)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.18, linewidth=0.35)

    legend_handles = [
        Line2D([0], [0], color=b[1], lw=2.2, label=f"{b[3]} ({by_bucket.get(b[3], 0):,})")
        for b in LANE_BUCKETS
    ]
    ax.legend(handles=legend_handles, loc="lower left", fontsize=9, framealpha=0.92)

    plt.tight_layout()
    plt.savefig(args.out, dpi=args.dpi)
    plt.close()

    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
