#!/usr/bin/env python3
"""
Compute speed table inputs for reports:
- Max IT (Private Transport / car) speed from network freespeed (km/h)
- Max OT (Public Transport / pt) speed from freespeed along PT route links

Inputs (defaults):
- scenarios/shamalgan/network.xml
- scenarios/shamalgan/transitSchedule.xml

Output (default):
- analysis-artifacts/speed-tables/speed_limits_shamalgan.csv

Notes:
- We use a robust statistic (p95) rather than absolute max to avoid outliers.
- This is NOT a "factual speed after congestion" metric. It is a speed limit proxy from input freespeed.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    xs = sorted(values)
    k = (len(xs) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if c == f:
        return xs[f]
    d0 = xs[f] * (c - k)
    d1 = xs[c] * (k - f)
    return d0 + d1


def read_network_freespeeds_kmh(network_xml: Path) -> dict[str, float]:
    tree = ET.parse(network_xml)
    root = tree.getroot()
    speeds: dict[str, float] = {}
    for link in root.findall(".//link"):
        link_id = link.attrib.get("id")
        fs = link.attrib.get("freespeed")
        if not link_id or fs is None:
            continue
        try:
            fs_ms = float(fs)
        except ValueError:
            continue
        speeds[link_id] = fs_ms * 3.6
    return speeds


def iter_pt_route_link_ids(transit_schedule_xml: Path) -> Iterable[str]:
    tree = ET.parse(transit_schedule_xml)
    root = tree.getroot()
    # MATSim schedule uses <transitLine><transitRoute><route><link refId="..."/>
    for link in root.findall(".//transitRoute/route/link"):
        ref = link.attrib.get("refId")
        if ref:
            yield ref


def write_csv(
    out_csv: Path,
    *,
    network_links: int,
    pt_route_links: int,
    it_p50: float,
    it_p95: float,
    ot_p50: float,
    ot_p95: float,
) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "metric",
                "value_kmh",
                "notes",
            ]
        )
        w.writerow(["network_links", network_links, "count of links in network.xml"])
        w.writerow(["pt_route_links", pt_route_links, "count of route links referenced in transitSchedule.xml"])
        w.writerow(["it_freespeed_p50", f"{it_p50:.3f}", "median freespeed across network links"])
        w.writerow(["it_freespeed_p95", f"{it_p95:.3f}", "p95 freespeed across network links (proxy for max IT speed)"])
        w.writerow(["ot_freespeed_p50", f"{ot_p50:.3f}", "median freespeed along PT route links"])
        w.writerow(["ot_freespeed_p95", f"{ot_p95:.3f}", "p95 freespeed along PT route links (proxy for max OT speed)"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", type=Path, default=ROOT / "scenarios" / "shamalgan" / "network.xml")
    ap.add_argument("--schedule", type=Path, default=ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml")
    ap.add_argument("--out", type=Path, default=ROOT / "analysis-artifacts" / "speed-tables" / "speed_limits_shamalgan.csv")
    args = ap.parse_args()

    link_speed = read_network_freespeeds_kmh(args.network)
    all_speeds = list(link_speed.values())
    if not all_speeds:
        raise SystemExit(f"No freespeed values found in {args.network}")

    pt_link_ids = list(iter_pt_route_link_ids(args.schedule))
    pt_speeds = [link_speed[lid] for lid in pt_link_ids if lid in link_speed]

    it_p50 = statistics.median(all_speeds)
    it_p95 = percentile(all_speeds, 95)
    ot_p50 = statistics.median(pt_speeds) if pt_speeds else float("nan")
    ot_p95 = percentile(pt_speeds, 95) if pt_speeds else float("nan")

    write_csv(
        args.out,
        network_links=len(all_speeds),
        pt_route_links=len(pt_speeds),
        it_p50=it_p50,
        it_p95=it_p95,
        ot_p50=ot_p50,
        ot_p95=ot_p95,
    )

    print(f"Saved: {args.out}")
    print(f"IT freespeed: p50={it_p50:.2f} km/h, p95={it_p95:.2f} km/h")
    if pt_speeds:
        print(f"OT freespeed along PT routes: p50={ot_p50:.2f} km/h, p95={ot_p95:.2f} km/h")
    else:
        print("OT freespeed along PT routes: n/a (no PT links matched to network)")


if __name__ == "__main__":
    main()

