# Handoff по Шамалгану

Краткая «памятка» для быстрого старта новой сессии.

**English:** [SHAMALGAN_HANDOFF](../../en/root/SHAMALGAN_HANDOFF.md)

## Текущий статус

- Сценарий Шамалган перенесён в репозиторий на базе scenario-template.
- Сборка проходит: `mvnw -DskipTests compile`.
- Класс запуска: `org.matsim.project.RunShamalgan`.

## Перенесённое содержимое

- `scenarios/shamalgan/*`
- `original-input-data/shamalgan/*`
- `src/main/java/org/matsim/project/*`
- `tools/derive_shamalgan_zones.py`
- `analysis-artifacts/zone-derivation/*`

## Важные документы

- `scenarios/shamalgan/README.md`
- `scenarios/shamalgan/POPULATION_ALGORITHM.md`
- `docs/en/root/README_SHAMALGAN.md` (EN) / `docs/ru/root/README_SHAMALGAN.md` (RU)

## Факты по моделированию

- Режим `pt` в планах пока только метка; расписание/транспорт не загружались.
- Реальный ОТ требует расписание и транспорт (обычно из GTFS).
- SimWrapper строит дашборды после прогона в `output/` (`dashboard-*.yaml`, `analysis/`).

## Быстрые команды

```powershell
.\mvnw.cmd -q -DskipTests compile
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643"
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml"
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=--simwrapper"
```

## При тормозах

- Исключить из индексации IDE: `output/`, `scenarios/shamalgan/output/`, `analysis-artifacts/`.
- Долгие прогоны запускать из терминала.

## Следующие шаги

1. Подключить реальный ОТ (GTFS → расписание и транспорт MATSim).
2. При необходимости — перепланирование выбора режима.
3. Свой дашборд SimWrapper под КПЭ Шамалгана.
