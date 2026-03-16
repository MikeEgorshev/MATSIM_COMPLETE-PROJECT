#!/usr/bin/env python3
"""
Build an interactive HTML map of PT routes with 2GIS / Yandex basemap.
Converts coordinates from EPSG:32643 to WGS84 and draws routes along link geometry.
Also draws the MATSim road network (same link segments) so PT routes clearly sit on our segments.
Output: Visualization/pt_routes_map.html
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "scenarios" / "shamalgan" / "network-with-pt.xml"
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
OUT_HTML = ROOT / "Visualization" / "pt_routes_map.html"

# Фирменные цвета по линиям, согласованные с инфографикой:
# 6  → синий, 11 → зелёный, 213 → оранжевый, 256 → фиолетовый.
LINE_COLORS = {
    "line_6": "#1D4ED8",
    "line_11": "#15803D",
    "line_213": "#EA580C",
    "line_256": "#7E22CE",
}

# Запасные цвета (если появятся дополнительные линии).
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


def main():
    transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

    def to_wgs84(x: float, y: float) -> tuple[float, float]:
        lon, lat = transformer.transform(x, y)
        return (lat, lon)  # Leaflet uses [lat, lng]

    nodes, links = read_network(NETWORK)
    facilities, routes = read_schedule(SCHEDULE)
    if not routes:
        raise RuntimeError("No routes found in transitSchedule.xml")

    route_data = []
    line_summary: dict[str, dict] = {}
    all_lat, all_lng = [], []
    for line_id, route_id, link_refs, stop_coords in routes:
        if link_refs:
            pts = build_route_polyline(link_refs, links, nodes)
        else:
            pts = stop_coords
        if not pts:
            continue
        latlngs = [to_wgs84(x, y) for x, y in pts]
        stops = [to_wgs84(x, y) for x, y in stop_coords]
        for (lat, lng) in latlngs + stops:
            all_lat.append(lat)
            all_lng.append(lng)
        route_data.append(
            {
                "line_id": line_id,
                "route_id": route_id,
                "latlngs": latlngs,
                "stops": stops,
                "n_stops": len(stop_coords),
            }
        )

        # агрегированная статистика по линии (для легенды)
        s = line_summary.setdefault(line_id, {"dirs": 0, "stops": 0})
        s["dirs"] += 1
        s["stops"] += len(stop_coords)

    if not route_data:
        raise RuntimeError("No route geometry to draw")
    center_lat = (min(all_lat) + max(all_lat)) / 2
    center_lng = (min(all_lng) + max(all_lng)) / 2
    colors_js = json.dumps(COLORS)

    # Build network layer: all links as segments (same geometry as PT uses), in bbox
    all_pts = []
    for r in route_data:
        for ll in r.get("latlngs", []) + r.get("stops", []):
            all_pts.append(ll)
    if all_pts:
        lats = [p[0] for p in all_pts]
        lngs = [p[1] for p in all_pts]
        margin = 0.001
        bbox_lat_min = min(lats) - margin
        bbox_lat_max = max(lats) + margin
        bbox_lng_min = min(lngs) - margin
        bbox_lng_max = max(lngs) + margin
    else:
        bbox_lat_min = bbox_lat_max = center_lat
        bbox_lng_min = bbox_lng_max = center_lng

    network_segments = []
    for link in links.values():
        fr = nodes.get(link["from"])
        to = nodes.get(link["to"])
        if not fr or not to:
            continue
        lat1, lng1 = to_wgs84(fr[0], fr[1])
        lat2, lng2 = to_wgs84(to[0], to[1])
        if all_pts:
            if (lat1 < bbox_lat_min and lat2 < bbox_lat_min) or (lat1 > bbox_lat_max and lat2 > bbox_lat_max):
                continue
            if (lng1 < bbox_lng_min and lng2 < bbox_lng_min) or (lng1 > bbox_lng_max and lng2 > bbox_lng_max):
                continue
        network_segments.append([[lat1, lng1], [lat2, lng2]])
    network_segments_js = json.dumps(network_segments)
    line_summary_js = json.dumps(line_summary, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Shamalgan PT — карта маршрутов</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <style>
    body {{ margin: 0; font-family: "Segoe UI", Arial, sans-serif; }}
    #map {{ width: 100%; height: 100vh; }}
    .legend {{ position: absolute; bottom: 24px; left: 12px; z-index: 1000; background: #fff; padding: 10px 14px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 12px; max-height: 50vh; overflow-y: auto; }}
    .legend h3 {{ margin: 0 0 8px 0; font-size: 14px; }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; }}
    .legend-swatch {{ width: 20px; height: 4px; border-radius: 2px; }}
    .legend-hint {{ margin: 4px 0 8px 0; font-size: 11px; color: #555; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="legend">
    <h3>Маршруты ОТ</h3>
    <p class="legend-hint">Маршруты построены по звеньям сети MATSim (отрезки узлов). Серый слой — та же сеть.</p>
    <div id="legendItems"></div>
  </div>
  <script>
    const routeData = {json.dumps(route_data, ensure_ascii=False)};
    const colors = {colors_js};
    const networkSegments = {network_segments_js};
    const lineSummary = {line_summary_js};
    // Фиксированные цвета линий (как в инфографике)
    const LINE_COLORS = {{
      "line_6": "#1D4ED8",
      "line_11": "#15803D",
      "line_213": "#EA580C",
      "line_256": "#7E22CE",
    }};

    const map = L.map("map", {{ center: [{center_lat}, {center_lng}], zoom: 13 }});

    // OSM (работает без ключа)
    const osm = L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      attribution: "© OpenStreetMap",
      maxZoom: 19
    }});

    // Яндекс.Карты (подложка) — без ключа, базовые тайлы
    const yandex = L.tileLayer("https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={{x}}&y={{y}}&z={{z}}&scale=1&lang=ru_RU", {{
      attribution: "© Яндекс",
      maxZoom: 19
    }});

    // Яндекс (официальный Tiles API — нужен ключ: https://yandex.ru/dev/maps/ )
    const yandexApi = L.tileLayer("https://tiles.api-maps.yandex.ru/v1/tiles?x={{x}}&y={{y}}&z={{z}}&lang=ru_RU&l=map&apikey=YOUR_YANDEX_API_KEY", {{
      attribution: "© Яндекс",
      maxZoom: 19
    }});

    // 2GIS — нужен API-ключ: https://dev.2gis.com/ → подставить в key=
    const dgisUrl = "https://tile0.maps.2gis.com/v2/tiles/online_hd/{{z}}/{{x}}/{{y}}.png?key=YOUR_2GIS_KEY";
    const dgis = L.tileLayer(dgisUrl, {{
      attribution: "© 2GIS",
      maxZoom: 19
    }});

    osm.addTo(map);

    // Сеть MATSim (те же звенья, по которым идут маршруты ОТ) — чтобы видеть совпадение
    const networkLayer = L.layerGroup();
    networkSegments.forEach(seg => {{
      L.polyline(seg, {{ color: "#6b7280", weight: 2, opacity: 0.7 }}).addTo(networkLayer);
    }});
    networkLayer.addTo(map);

    // Отдельный слой для каждой линии ОТ, чтобы можно было включать/выключать маршруты
    const lineLayers = {{}};
    routeData.forEach((r, i) => {{
      const baseColor = LINE_COLORS[r.line_id] || colors[i % colors.length];
      const color = baseColor;
      if (!lineLayers[r.line_id]) {{
        lineLayers[r.line_id] = L.layerGroup().addTo(map);
      }}
      const group = lineLayers[r.line_id];
      L.polyline(r.latlngs, {{ color, weight: 4, opacity: 0.9 }}).addTo(group);
      r.stops.forEach(ll => {{
        L.circleMarker(ll, {{ radius: 5, fillColor: color, color: "#fff", weight: 1, fillOpacity: 1 }}).addTo(group);
      }});
    }});

    const overlays = {{ "Сеть MATSim (звенья)": networkLayer }};
    Object.keys(lineLayers).sort().forEach(lineId => {{
      const num = lineId.replace("line_", "");
      overlays["Маршрут " + num] = lineLayers[lineId];
    }});

    L.control.layers(
      {{ "OpenStreetMap": osm, "Яндекс": yandex, "Яндекс (API)": yandexApi, "2GIS": dgis }},
      overlays,
      {{ collapsed: false }}
    ).addTo(map);

    // Legend (по одной строке на линию, а не на каждое направление)
    const legendEl = document.getElementById("legendItems");
    Object.keys(lineSummary).sort().forEach((lineId, idx) => {{
      const info = lineSummary[lineId];
      const color = LINE_COLORS[lineId] || colors[idx % colors.length];
      const div = document.createElement("div");
      div.className = "legend-item";
      const num = lineId.replace("line_", "");
      div.innerHTML = '<span class="legend-swatch" style="background:' + color + '"></span>' +
                      '<span>Маршрут ' + num + ': ' + info.stops + ' ост., ' + info.dirs + ' направл.</span>';
      legendEl.appendChild(div);
    }});

    map.fitBounds(L.latLngBounds(routeData.flatMap(r => r.latlngs.concat(r.stops))), {{ padding: [40, 40] }});
  </script>
</body>
</html>
"""

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Saved: {OUT_HTML}")
    print(f"Routes: {len(route_data)}. Open in browser; use layer control (top-right) for 2GIS / Yandex.")


if __name__ == "__main__":
    main()
