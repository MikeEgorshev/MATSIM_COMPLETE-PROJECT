# Сценарий MATSim Шамалган

Транспортная модель **Шамалган (Жибек Жолы), Казахстан** на базе MATSim.

**Документация:** [English](../../en/root/README.md) | [Русский](.)

В репозитории:
- Дорожная сеть по OSM (`scenarios/shamalgan/network.xml`)
- Синтетическое население по зонам (`scenarios/shamalgan/population.xml`)
- ОТ по остановкам OSM (`scenarios/shamalgan/transitSchedule.xml`, `transitVehicles.xml`)
- Сеть с ОТ (`scenarios/shamalgan/network-with-pt.xml`)
- Артефакты анализа и скрипты (`analysis-artifacts/`, `tools/`)

## Цель

Воспроизводимый базовый сценарий Шамалгана с постепенной заменой допущений реальными данными.

ОТ сейчас:
- Полноценного GTFS по коридору Алматы/Шамалган пока нет.
- Расписание ОТ строится по допущениям на основе остановок OSM.
- Параметры: скорость 30 км/ч, стоянка 60 с, интервал 360 с (6 мин), окно 06:00–23:00.

## Быстрый старт

Сборка:

```powershell
.\mvnw.cmd -q -DskipTests compile
```

Запуск сценария по умолчанию:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan"
```

Запуск с ОТ и дашбордами SimWrapper:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=scenarios/shamalgan/config.xml --simwrapper"
```

Построение ОТ по остановкам OSM (без GTFS):

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromAssumptions" "-Dexec.args=scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00"
```

Архивация старых выходов (оставить последний):

```powershell
powershell -ExecutionPolicy Bypass -File tools\archive_outputs.ps1 -KeepLatest 1
```

## Структура репозитория

- `scenarios/shamalgan/`: входы и конфиги сценария
- `original-input-data/shamalgan/`: исходные данные (OSM, растр, шаблоны)
- `src/main/java/org/matsim/project/`: классы подготовки и запуска Шамалгана
- `tools/`: скрипты извлечения, QC, построения графиков
- `analysis-artifacts/`: отчёты и справочные материалы по ОТ
- [docs/ru/progress/](../progress/): прогресс и статус работ

## Данные и лицензии

- Код: см. `LICENSE`.
- Данные в `original-input-data/` могут иметь отдельные лицензии; перед распространением проверять.

## См. также

- [Установка на новом ПК](NEW_PC_SETUP.md)
- [Журнал запусков и решений](README_RUNNING.md)
- [Руководство по запуску Шамалгана](README_SHAMALGAN.md)
- [Handoff](SHAMALGAN_HANDOFF.md)
- [План интеграции ОТ](SHAMALGAN_REAL_PT_INTEGRATION_PLAN.md)
- [Архив](../../archive/) — память сессий и профиль преемственности (исторические)
