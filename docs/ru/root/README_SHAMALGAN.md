# Миграция Шамалгана (из matsim-example-project)

Сценарий Шамалган перенесён в репозиторий на базе MATSim scenario-template.

**English:** [README_SHAMALGAN](../../en/root/README_SHAMALGAN.md)

## Перенесённые пути

- `scenarios/shamalgan/*`
- `original-input-data/shamalgan/*`
- `src/main/java/org/matsim/project/*`
- `tools/derive_shamalgan_zones.py`
- `analysis-artifacts/zone-derivation/*`

## Команды запуска

Из корня репозитория:

```powershell
.\mvnw.cmd -q -DskipTests compile
```

Создание сети из OSM:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643"
```

Создание сети с консервативным профилем дорог:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643 poor"
```

Население по зонам:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml"
```

Запуск сценария:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan"
```

С дашбордами SimWrapper:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=--simwrapper"
```

ОТ из GTFS:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromGtfs" "-Dexec.args=original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip scenarios/shamalgan/network.xml scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 2026-02-01 mergeStopsAtSameCoord false"
```

ОТ по допущениям (остановки OSM):

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromAssumptions" "-Dexec.args=scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00"
```

Запуск с ОТ:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=scenarios/shamalgan/config-pt.xml --simwrapper"
```

Архивация выходов:

```powershell
powershell -ExecutionPolicy Bypass -File tools\archive_outputs.ps1 -KeepLatest 1
```

## Замечания

- Основной класс в `pom.xml`: `org.matsim.project.RunShamalgan`.
- Код Gunma в репозитории не мешает запуску Шамалгана.
- Параметры ОТ по допущениям: `scenarios/shamalgan/PT_BOOTSTRAP_SETTINGS.md`.
- Базовые примеры ОТ: `analysis-artifacts/pt-data/MATSIM_EXAMPLE_PT_BASELINES.md`.
