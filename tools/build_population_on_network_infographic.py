#!/usr/bin/env python3
"""
Build infographic: distribution of agents (home / work / other) over the road network.

Task (from docs/ru/progress/07_uds_pt_population_analysis.md):
- Input: population.xml (MATSim plans), network-with-pt.xml or network.xml
- Output: population_by_link.csv, population_on_network_map.png (and optional .html)
- CRS: EPSG:32643; for HTML/display can use WGS84.

Usage:
  python tools/build_population_on_network_infographic.py
  python tools/build_population_on_network_infographic.py [path/to/population.xml]
"""

from __future__ import annotations

import csv
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POPULATION = ROOT / "scenarios" / "shamalgan" / "population.xml"
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
ZONES_CSV = ROOT / "original-input-data" / "shamalgan" / "zones-derived.csv"
OUT_DIR = ROOT / "analysis-artifacts"
OUT_CSV = OUT_DIR / "population_by_link.csv"
OUT_PNG = OUT_DIR / "population_on_network_map.png"
OUT_HTML = ROOT / "Visualization" / "population_on_network_map.html"
TOP_LINKS_LABELS = 12  # number of top links to show count on map
TOP_ZONES_CHART = 20   # number of zones in work/home ratio chart


def open_population(path: Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Population file not found: {path}")
    if path.suffix == ".gz" or path.name.endswith(".xml.gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def count_activities_by_link(path: Path) -> tuple[dict[str, dict], int]:
    """
    Parse MATSim population XML and count activities per link by type.
    Returns (link_id -> { "home": n, "work": n, "other": n }, total_activities).
    Activity element: type=, link= (or link_id in some versions).
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"home": 0, "work": 0, "other": 0})
    total = 0
    with open_population(path) as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "activity":
                atype = (elem.get("type") or "").strip().lower()
                if atype not in ("home", "work", "other"):
                    atype = "other"
                link_id = elem.get("link") or elem.get("link_id") or elem.get("linkId")
                if link_id:
                    counts[link_id][atype] += 1
                    total += 1
                elem.clear()
    return dict(counts), total


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


def load_zones(path: Path) -> list[tuple[str, float, float]]:
    """Load zones-derived.csv: (zone_id, home_x, home_y)."""
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            zid = row.get("zone_id", "").strip()
            try:
                x = float(row.get("home_x", 0))
                y = float(row.get("home_y", 0))
            except (ValueError, TypeError):
                continue
            out.append((zid, x, y))
    return out


def aggregate_by_zone(
    link_counts: dict[str, dict],
    links: dict,
    nodes: dict,
    zones: list[tuple[str, float, float]],
) -> list[tuple[str, int, int, int, float]]:
    """For each link with counts, assign to nearest zone; return (zone_id, home, work, other, work_home_ratio) sorted by total desc."""
    zone_centroids = [(z[0], (z[1], z[2])) for z in zones]
    zone_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"home": 0, "work": 0, "other": 0})
    for link_id, c in link_counts.items():
        link = links.get(link_id)
        if not link:
            continue
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            continue
        cx = (fr[0] + to[0]) / 2
        cy = (fr[1] + to[1]) / 2
        best_z = None
        best_d2 = 1e30
        for zid, (zx, zy) in zone_centroids:
            d2 = (cx - zx) ** 2 + (cy - zy) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_z = zid
        if best_z:
            zone_totals[best_z]["home"] += c["home"]
            zone_totals[best_z]["work"] += c["work"]
            zone_totals[best_z]["other"] += c["other"]
    result = []
    for zid, c in zone_totals.items():
        total = c["home"] + c["work"] + c["other"]
        if total == 0:
            continue
        ratio = c["work"] / c["home"] if c["home"] else 0.0
        result.append((zid, c["home"], c["work"], c["other"], ratio))
    result.sort(key=lambda r: -(r[1] + r[2] + r[3]))
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Population-on-network infographic")
    parser.add_argument("population", nargs="?", default=str(DEFAULT_POPULATION), help="Path to population.xml or .xml.gz")
    parser.add_argument("--no-png", action="store_true", help="Skip PNG map (only CSV)")
    parser.add_argument("--html", action="store_true", help="Also write HTML map to Visualization/")
    args = parser.parse_args()

    pop_path = Path(args.population)
    print(f"Reading population: {pop_path}")
    link_counts, total_activities = count_activities_by_link(pop_path)
    if not link_counts:
        print("No activities with link reference found. Ensure population.xml has activity link attributes.")
        return

    # CSV: link_id, home, work, other, total
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for link_id, c in link_counts.items():
        home = c["home"]
        work = c["work"]
        other = c["other"]
        rows.append({
            "link_id": link_id,
            "home": home,
            "work": work,
            "other": other,
            "total": home + work + other,
        })
    rows.sort(key=lambda r: -r["total"])

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["link_id", "home", "work", "other", "total"])
        w.writeheader()
        w.writerows(rows)
    print(f"Saved: {OUT_CSV} ({len(rows)} links, {total_activities} activities)")

    nodes, links = read_network(NETWORK)
    # Build segments for links that have counts (for map extent and drawing)
    segments_with_counts = []
    all_x, all_y = [], []
    for link_id, c in link_counts.items():
        link = links.get(link_id)
        if not link:
            continue
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            continue
        total = c["home"] + c["work"] + c["other"]
        segments_with_counts.append((fr, to, c["home"], c["work"], c["other"], total))
        all_x.extend([fr[0], to[0]])
        all_y.extend([fr[1], to[1]])

    if not segments_with_counts:
        print("No link geometry found for counted links. Skipping map.")
        return

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    pad_x = max(1e-9, max_x - min_x) * 0.05
    pad_y = max(1e-9, max_y - min_y) * 0.05
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y

    if not args.no_png:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.gridspec import GridSpec
            from matplotlib.lines import Line2D
        except ImportError:
            print("matplotlib not installed. Skipping PNG. Use --no-png to suppress this.")
        else:
            # Global totals for text box
            sum_home = sum(r[2] for r in segments_with_counts)
            sum_work = sum(r[3] for r in segments_with_counts)
            sum_other = sum(r[4] for r in segments_with_counts)
            work_home_ratio = sum_work / sum_home if sum_home else 0.0
            n_agents_approx = total_activities // 3  # rough: 3 activities per agent (home-work-home or home-other-home)

            # Zone aggregates for bar chart
            zones = load_zones(ZONES_CSV)
            zone_stats = aggregate_by_zone(link_counts, links, nodes, zones)[:TOP_ZONES_CHART]

            fig = plt.figure(figsize=(18, 10))
            gs = GridSpec(1, 2, width_ratios=[1.4, 1], figure=fig)
            ax_map = fig.add_subplot(gs[0])
            ax_chart = fig.add_subplot(gs[1])

            # --- Map ---
            ax_map.set_aspect("equal")
            ax_map.set_xlim(min_x, max_x)
            ax_map.set_ylim(min_y, max_y)
            ax_map.set_xlabel("X (EPSG:32643)")
            ax_map.set_ylabel("Y (EPSG:32643)")
            ax_map.set_title("Распределение активностей по звеньям сети (дом / работа / другое)")

            max_total = max(r[5] for r in segments_with_counts) or 1
            # Sort by total for labels: take top segments
            segs_sorted = sorted(segments_with_counts, key=lambda r: -r[5])
            top_for_labels = set(id(s) for s in segs_sorted[:TOP_LINKS_LABELS])
            for seg in segments_with_counts:
                (x1, y1), (x2, y2), home, work, other, total = seg
                w = 0.5 + 3.0 * (total / max_total) ** 0.5
                if total == 0:
                    color = "#cccccc"
                else:
                    h_share = home / total
                    rr = 0.2 + 0.8 * (1 - h_share)
                    gg = 0.4 + 0.3 * h_share
                    bb = 0.8 * h_share
                    color = (rr, gg, bb)
                ax_map.plot([x1, x2], [y1, y2], color=color, linewidth=w, solid_capstyle="round")
                # Numeric label on top links
                if id(seg) in top_for_labels:
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    ax_map.text(mx, my, str(total), fontsize=8, ha="center", va="center",
                                color="black", fontweight="bold",
                                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85, edgecolor="none"))

            # Summary text box on map
            text_lines = [
                f"Всего активностей: {total_activities:,}",
                f"≈ агентов (план): {n_agents_approx:,}",
                f"Дом: {sum_home:,}   Работа: {sum_work:,}   Другое: {sum_other:,}",
                f"Соотношение работа/дом: {work_home_ratio:.2f}",
            ]
            ax_map.text(0.02, 0.98, "\n".join(text_lines), transform=ax_map.transAxes,
                        fontsize=10, verticalalignment="top", horizontalalignment="left",
                        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="gray"),
                        family="monospace")

            ax_map.legend(
                handles=[
                    Line2D([0], [0], color="#4a90d9", lw=3, label="Преимущественно дом"),
                    Line2D([0], [0], color="#d96a2c", lw=3, label="Преимущественно работа/другое"),
                ],
                loc="upper left",
            )

            # --- Bar chart: work/home ratio by zone (top zones) ---
            if zone_stats:
                zids = [z[0] for z in zone_stats]
                home_vals = [z[1] for z in zone_stats]
                work_vals = [z[2] for z in zone_stats]
                x_max = max(home_vals + work_vals)
                y_pos = range(len(zids))
                ax_chart.barh([i - 0.2 for i in y_pos], home_vals, height=0.35, label="Дом", color="#4a90d9", alpha=0.9)
                ax_chart.barh([i + 0.2 for i in y_pos], work_vals, height=0.35, label="Работа", color="#d96a2c", alpha=0.9)
                ax_chart.set_yticks(y_pos)
                ax_chart.set_yticklabels(zids, fontsize=8)
                ax_chart.set_xlabel("Число активностей")
                ax_chart.set_title("Соотношение работа/дом по зонам (топ-20 по числу активностей)")
                ax_chart.set_xlim(0, x_max * 1.18)
                ax_chart.text(x_max * 1.09, -1.5, "раб/дом", fontsize=7, color="gray", ha="left")
                ax_chart.legend(loc="lower right", fontsize=9)
                # Ratio as text at the end of each row
                for i, (zid, h, w, o, ratio) in enumerate(zone_stats):
                    ax_chart.text(x_max * 1.06, i, f" {ratio:.2f}", fontsize=7, va="center", color="gray")
                ax_chart.invert_yaxis()
            else:
                ax_chart.text(0.5, 0.5, "Зоны не загружены\n(zones-derived.csv)",
                              transform=ax_chart.transAxes, ha="center", va="center", fontsize=12)

            fig.tight_layout()
            fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved: {OUT_PNG}")

    if args.html:
        try:
            from pyproj import Transformer
        except ImportError:
            print("pyproj not installed. Skipping HTML map.")
        else:
            transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
            def to_wgs84(x, y):
                lon, lat = transformer.transform(x, y)
                return [lat, lon]

            sum_home = sum(r[2] for r in segments_with_counts)
            sum_work = sum(r[3] for r in segments_with_counts)
            sum_other = sum(r[4] for r in segments_with_counts)
            work_home_ratio = sum_work / sum_home if sum_home else 0
            n_agents_approx = total_activities // 3
            zones = load_zones(ZONES_CSV)
            zone_stats = aggregate_by_zone(link_counts, links, nodes, zones)[:TOP_ZONES_CHART]

            segments_geojson = []
            for (x1, y1), (x2, y2), home, work, other, total in segments_with_counts:
                segments_geojson.append({
                    "latlngs": [to_wgs84(x1, y1), to_wgs84(x2, y2)],
                    "home": home, "work": work, "other": other, "total": total,
                })
            center_lat = (min(all_y) + max(all_y)) / 2
            center_lng = (min(all_x) + max(all_x)) / 2
            center_wgs84 = to_wgs84(center_lng, center_lat)
            import json
            zone_data_js = json.dumps([{"zone_id": z[0], "home": z[1], "work": z[2], "ratio": round(z[4], 2)} for z in zone_stats], ensure_ascii=False)

            out_dir_html = OUT_HTML.parent
            out_dir_html.mkdir(parents=True, exist_ok=True)
            html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Население по сети — Shamalgan</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <style>
    body {{ margin: 0; }}
    #map {{ width: 100%; height: 100vh; }}
    .legend {{ position: absolute; bottom: 20px; left: 12px; z-index: 1000; background: #fff; padding: 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 12px; max-width: 320px; }}
    .legend table {{ border-collapse: collapse; margin-top: 6px; font-size: 11px; }}
    .legend th {{ text-align: left; padding: 2px 6px 2px 0; }}
    .legend td {{ padding: 2px 6px 2px 0; }}
    .stats {{ font-weight: bold; margin-bottom: 4px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="legend">
    <div class="stats">Активности по звеньям</div>
    <div>Всего активностей: {total_activities:,} &nbsp; ≈ агентов: {n_agents_approx:,}</div>
    <div>Дом: {sum_home:,} &nbsp; Работа: {sum_work:,} &nbsp; Другое: {sum_other:,}</div>
    <div>Соотношение работа/дом: {work_home_ratio:.2f}</div>
    <div style="margin-top:8px"><strong>Топ-20 зон (раб/дом):</strong></div>
    <table><thead><tr><th>Зона</th><th>Дом</th><th>Работа</th><th>раб/дом</th></tr></thead><tbody id="zoneRows"></tbody></table>
  </div>
  <script>
    const segments = {json.dumps(segments_geojson)};
    const zoneData = {zone_data_js};
    const maxTotal = Math.max(...segments.map(s => s.total), 1);
    const map = L.map("map").setView({json.dumps(center_wgs84)}, 12);
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{ attribution: "© OSM" }}).addTo(map);
    segments.forEach(s => {{
      const w = 0.5 + 3 * Math.sqrt(s.total / maxTotal);
      const h = s.total ? s.home / s.total : 0;
      const r = 0.2 + 0.8 * (1 - h);
      const g = 0.4 + 0.3 * h;
      const b = 0.8 * h;
      const color = `rgb(${{Math.round(r*255)}}, ${{Math.round(g*255)}}, ${{Math.round(b*255)}})`;
      L.polyline(s.latlngs, {{ color, weight: w, opacity: 0.9 }}).addTo(map);
    }});
    document.getElementById("zoneRows").innerHTML = zoneData.map(z =>
      `<tr><td>${{z.zone_id}}</td><td>${{z.home}}</td><td>${{z.work}}</td><td>${{z.ratio}}</td></tr>`
    ).join("");
  </script>
</body>
</html>
"""
            OUT_HTML.write_text(html_content, encoding="utf-8")
            print(f"Saved: {OUT_HTML}")


if __name__ == "__main__":
    main()
