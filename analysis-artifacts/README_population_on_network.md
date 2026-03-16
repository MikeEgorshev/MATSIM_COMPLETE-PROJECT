# Инфографика: население по звеньям сети

Распределение активностей (дом / работа / другое) по link id для отчёта по УДС, ОТ и населению (см. [07_uds_pt_population_analysis.md](../docs/ru/progress/07_uds_pt_population_analysis.md)).

## Файлы

| Файл | Описание |
|------|----------|
| `population_by_link.csv` | По каждому link_id: число активностей home, work, other, total (отсортировано по total по убыванию). |
| `population_on_network_map.png` | Карта: звенья с активностями, цвет — доля «дом» (синий) vs «работа/другое» (оранжевый), толщина линии — количество. CRS: EPSG:32643. |

Интерактивная карта с подложкой OSM: [Visualization/population_on_network_map.html](../Visualization/population_on_network_map.html).

## Как сгенерировать

```bash
python tools/build_population_on_network_infographic.py
```

Входные данные: `scenarios/shamalgan/population.xml`, `scenarios/shamalgan/network-with-pt.xml`.

Опции:
- `--no-png` — только CSV.
- `--html` — дополнительно записать HTML-карту в `Visualization/`.
