# Визуализации

Здесь хранятся все артефакты визуализации проекта (карты ОТ, сети, зон и т.д.).

**Карта системы ОТ в текущем состоянии:**
- `pt_routes_map.svg` — маршруты из `scenarios/shamalgan/transitSchedule.xml` (линии по линкам, статичная картинка).
- **`pt_routes_map.html`** — интерактивная карта с подложкой **2GIS / Яндекс**: открой в браузере, в правом верхнем углу переключатель слоёв (OpenStreetMap, Яндекс, 2GIS). Генерация: `python tools/build_pt_map_html.py`.

**Подложки 2GIS и Яндекс:** в сгенерированном HTML по умолчанию доступны OSM и попытка загрузки тайлов Яндекса без ключа. Чтобы гарантированно использовать 2GIS или официальные тайлы Яндекса, подставьте API-ключи в `Visualization/pt_routes_map.html` (поиск по строкам `YOUR_2GIS_KEY` и `YOUR_YANDEX_API_KEY`). Ключи: [2GIS](https://dev.2gis.com/), [Яндекс.Карты](https://yandex.ru/dev/maps/).

## Как сгенерировать

| Файл | Скрипт |
|------|--------|
| `pt_routes_map.svg` | `python tools/plot_pt_routes_svg.py` |
| **`pt_routes_map.html`** | **`python tools/build_pt_map_html.py`** (подложка 2GIS/Яндекс) |
| `assumed_pt_network_map.png` | `python tools/plot_assumed_pt_network.py` |
| `pt_network_infographic.png` | `python tools/build_pt_network_infographic.py` |
| `pt_network_interpretation.md` | (вместе с pt_network_infographic) |
| `pt_schedule_infographic.png` | `python tools/build_pt_schedule_infographic.py` |
| `network_lane_overview.png` | `python tools/plot_network_lane_overview.py` |
| `network_speed_overview.png` | `python tools/plot_network_speed_overview.py` |
| `osm_bus_stops_map.png` | `python tools/extract_shamalgan_bus_stops.py` |

Карты зон (zone-derivation) генерируются скриптом `tools/derive_shamalgan_zones.py` в `analysis-artifacts/zone-derivation/`; при необходимости их можно копировать сюда.
