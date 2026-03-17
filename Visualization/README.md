# Визуализации

Здесь хранятся все артефакты визуализации проекта (карты ОТ, сети, зон и т.д.). Всё, что не в `output/` (результаты прогонов MATSim), собрано здесь.

**Корень:**
- `pt_routes_map.svg` — маршруты ОТ по линкам (статичная картинка).
- **`pt_routes_map.html`** — интерактивная карта маршрутов с подложкой 2GIS/Яндекс.
- **`population_on_network_map.html`** — население по звеньям (подложка OSM).
- `population_on_network_map.png` — карта населения (статичная).

**Подложки 2GIS и Яндекс:** переключатель слоёв в правом верхнем углу в `pt_routes_map.html`. Подставьте API-ключи (поиск `YOUR_2GIS_KEY`, `YOUR_YANDEX_API_KEY`) при необходимости.

## Структура

| Папка / файл | Содержимое |
|--------------|------------|
| **network-qc/** | `network_lane_overview.png`, `network_speed_overview.png` — полосы и скорости по сети. |
| **pt-data/** | Инфографики ОТ: `pt_network_infographic.png`, `pt_schedule_infographic.png`, `assumed_pt_network_map.png`, `osm_bus_stops_map.png`, `pt_network_interpretation.md`. |
| **zone-derivation/** | Карты зон: `01_density_and_zones.png` … `07_population_capture_curve.png`, `04_*`, `05_*`, summary CSV. |
| **docs-progress/** | Картинки из docs/ru/progress/img: схемы маршрутов, сходимость, heatmap и т.д. |

## Как сгенерировать

| Файл | Скрипт |
|------|--------|
| `pt_routes_map.svg` | `python tools/plot_pt_routes_svg.py` |
| `pt_routes_map.html` | `python tools/build_pt_map_html.py` |
| `population_on_network_map.html` / `.png` | `python tools/build_population_on_network_infographic.py` (опция `--html` для HTML) |
| `network-qc/*.png` | `python tools/plot_network_lane_overview.py`, `python tools/plot_network_speed_overview.py` |
| `pt-data/assumed_pt_network_map.png` | `python tools/plot_assumed_pt_network.py` |
| `pt-data/pt_network_infographic.png` | `python tools/build_pt_network_infographic.py` |
| `pt-data/pt_schedule_infographic.png` | `python tools/build_pt_schedule_infographic.py` |
| `pt-data/osm_bus_stops_map.png` | `python tools/extract_shamalgan_bus_stops.py` |
| `zone-derivation/*.png` | `python tools/derive_shamalgan_zones.py` |
| `zone-derivation/08_zones_rectangles.png` | `python tools/plot_zones_rectangles.py` (сетка 10×8, прямоугольники по home_weight) |

Таблицы и отчёты (CSV, MD) по-прежнему в `analysis-artifacts/` (например `population_by_link.csv`).
