# Пайплайн разработки сценария MATSim

Документ фиксирует **воспроизводимый конвейер разработки сценария** MATSim, который мы будем дополнять по мере продвижения.

## 0) Старт: структура, `.gitignore` и правила хранения данных

- **`.gitignore` с первого коммита** — без этого репозиторий засоряется:
  ```
  scenarios/*/output*/
  scenarios/*/ITERS/
  *.gz
  *.log
  __pycache__/
  .idea/
  target/
  ```
- **Сценарий в отдельной папке**: `scenarios/`
  - `config.xml`
  - `network.xml`
  - `population.xml` 
  - `transitSchedule.xml`, `transitVehicles.xml`
  - `pt_service_profile.csv` (если используем профиль интервалов/скоростей)
  - `pt_route_overrides.json` (маршрутные ограничения: mandatory corridors, blocked links — **не в Java-коде**)
  - `README.md` (как собрать и запустить сценарий)
- **Входные данные**: `original-input-data/<city>/`
  - шейп моделируемой области (OSM XML extract)
  - растр плотности населения (GeoTIFF) для приведения в число населения или данные по населению из Visum
  - `zones-derived.csv`
  - при наличии: `new_map.gpkg` / набор слоёв с линками/точками/полигонами
- **Артефакты анализа**: `analysis-artifacts/<topic>/...`
  - QC отчёты, таблицы, изображения, промежуточные выгрузки
- **Визуализации**: `Visualization/`
  - SVG/PNG/HTML карты, чтобы быстро проверять данные и показывать результат
- **Принцип параметризации кода:** один класс `PrepareNetwork` / `PreparePopulation` / `PrepareTransit` / `RunScenario` с аргументами (город, CRS, профиль дорог), а не дублирование `PrepareShamalganNetwork` / `PrepareKaskelenNetwork`. Город-специфичные данные — в CSV/JSON/аргументах, не в Java-константах.

## 1) УДС: сборка дорожной сети и QC

**Цель:** получить MATSim-сеть, которая связна, без критических артефактов и с понятными атрибутами (`lanes`, `freespeed`, `capacity`).

- **1.1 OSM-экстракт**
  - подготовить `original-input-data/<city>/map` (границы, корректность, наличие `<bounds>`)
- **1.2 Генерация MATSim сети**
  - запуск конвертера OSM → MATSim (класс `PrepareNetwork`, аргументы: город, CRS, профиль дорог)
  - внутри: `SupersonicOsmNetworkReader` (MATSim core) + `NetworkCleaner` + lane policy из OSM-тегов
  - результат: `scenarios/<city>/network.xml`
- **1.3 QC сети**
  - связность (компоненты, изоляты, тупики)
  - длины линков (аномально длинные сегменты)
  - распределение `lanes`, `freespeed`, `capacity` (min/p50/p95/max)
- **1.4 Профиль “плохих дорог” (если нужно)**
  - осознанно занижать `capacity` и/или `freespeed` по классам дорог для сельской/низкокачественной сети
- **Выходы шага**
  - `network.xml` + QC отчёт и 1–2 инфографики (скорости/полосы)

## 2) Зоны и население: от плотности к агентам на сети

**Цель:** разместить агентов так, чтобы пространственная структура отражала карту плотности и (по возможности) точки притяжения.

- **2.1 Подготовка зон по плотности**
  - скрипт `tools/derive_*_zones.py`:
    - клип по OSM bounds
    - агрегация в регулярную сетку (в Шамалгане было порядка \(\approx 300 \times 300\) м по ячейке)
    - расчёт `home_weight`, `work_weight`
    - перепроекция в CRS проекта (например, EPSG:32643)
  - результат: `original-input-data/<city>/zones-derived.csv`
  - артефакты: карты зон/весов/coverage curve
- **2.2 Усиление “работы/притяжения”**
  - если есть точки POI (магазины/АЗС/коммерция) — усилить `work_weight` в зонах, где они лежат
- **2.3 Генерация населения (plans)**
  - `PreparePopulationFromZones` (параметризован по городу через аргументы):
    - выбор зоны дома пропорционально `home_weight`
    - выбор зоны работы/other пропорционально `work_weight`
    - размещение активности на линках (length-weighted в фиксированном окне вокруг центроида зоны)
    - **snap к ближайшему линку** сети (`nearest link`)
    - планы `home-work-home` / `home-other-home` + временные окна
  - результат: `scenarios/<city>/population.xml`
- **2.4 Визуализация распределения населения**
  - карта “активности по линкам” (HTML/PNG) + базовые sanity-check

## 3) ОТ: два пути — GTFS или bootstrap

**Цель:** получить работоспособное PT-предложение: остановки, маршруты, расписание — достаточные для тестового расчёта и первичных выводов.

### Путь A: GTFS (предпочтительный)
Если для города есть GTFS-фид (от оператора, из OpenMobilityData, или собранный вручную):
- конвертировать через `PrepareTransitFromGtfs` → `transitSchedule.xml` + `transitVehicles.xml`
- создать `network-with-pt.xml` (pseudo-network)
- **плюс:** реальное расписание, минимум допущений

### Путь B: bootstrap без GTFS (как в Шамалгане)
- **3.1 Остановки и атрибуты маршрутов**
  - источник: слой точек в GeoPackage/шейпе или ручная разметка
  - дополнить остановки, если покрытия недостаточно
  - атрибуты: `route_id`, `direction`, `stop_sequence` (+ `dwell_sec` опционально)
- **3.2 Привязка остановок к УДС**
  - snap stops → links
  - QA: расстояния snap, достижимость сегментов между соседними остановками
- **3.3 Построение трасс маршрутов**
  - базово: Dijkstra по сети между остановками
  - маршрутные ограничения (mandatory corridors, blocked links) — **в `pt_route_overrides.json`, не в Java-коде**
  - в Шамалгане route-specific хаки (`ROUTE_MANDATORY_LINK_OVERRIDES`, `ROUTE_213_BLOCKED_ORIGIDS`) были hardcoded — это ошибка, усложнявшая переиспользование
- **3.4 Синтез расписания**
  - окно обслуживания + headway по периодам (через `pt_service_profile.csv`)
  - выходы: `transitSchedule.xml`, `transitVehicles.xml`
- **3.5 PT-расширение сети**
  - `network-with-pt.xml` (pt-псевдолинки для маршрутизатора)

### Общее для обоих путей
- **3.6 Визуализация ОТ**
  - `pt_routes_map.html` (маршруты на подложке) + статичная SVG при необходимости
- **3.7 QA расписания**
  - `TransitScheduleValidator` (встроен в MATSim) — прогнать после генерации, до запуска

## 4) Конфиг и запуск MATSim (воспроизводимо)

**Цель:** сценарий запускается “из коробки”, выходы стабильны и пригодны для анализа.

- **4.1 Конфиг**
  - относительные пути к входам
  - `lastIteration`: 10 (smoke) → 100 (стабилизация)
  - потоки (threads), endTime (если PT может “тянуть хвост”)
  - PT routing (SwissRailRaptor), transfer penalty
  - mode choice (SubtourModeChoice: `car,pt,walk`)
- **4.2 Smoke-run**
  - короткий расчёт на 10 итераций
- **4.3 Полный расчёт**
  - 100 итераций (и/или отдельные расчёты для сравнения профилей сети)
- **4.4 SimWrapper**
  - запуск с `--simwrapper`
  - **важно:** каждый расчёт писать в отдельную папку `output_<tag>` (дата/параметры), чтобы избежать блокировок и потери истории

## 5) Анализ выходов и “приёмка” сценария

**Цель:** сформулировать “что работает”, “что сомнительно”, “что улучшать” — с опорой на артефакты.

- **5.1 Базовые KPI**
  - сходимость score, доли режимов, распределения времени/длины поездок
- **5.2 УДС**
  - нагрузка сети (volumes) и поиск узких мест
- **5.3 ОТ**
  - посадки/высадки по маршрутам и времени (из events)
  - проверка пустых/аномальных линий
- **5.4 Население**
  - карта home/work распределения по сети, sanity-check покрытия
- **5.5 Stuck agents**
  - анализ агентов, не завершивших план до конца дня (по часам, по линкам)
  - в Шамалгане это уже делали (`stuck_agents_per_hour.csv`, `stuck_agents_per_link.csv`) — включить в стандартный набор
- **5.6 Решение**
  - список «принять как есть» / «доработать» с приоритетами

## 5.5) Калибровка (при наличии данных)

**Цель:** довести модальные доли и объёмы до наблюдаемых значений.

- При наличии замеров (интенсивности на перекрёстках, данных APC по ОТ, обследований подвижности):
  - корректировка scoring-констант (`constant`, `monetaryDistanceRate`) по режимам
  - корректировка `additionalTransferTime` для ОТ
  - при необходимости: итеративный подбор `headway` / `dwell` в `pt_service_profile.csv`
- Без замеров (proof-of-concept): пропустить, но **зафиксировать** что калибровка не проводилась

## 6) Документация, отчётность и презентация

**Цель:** чтобы следующий человек мог повторить сборку и понять допущения.

- **6.1 Прогресс-доки**
  - `docs/ru/progress/01_network.md`, `02_population.md`, `03_pt.md`, `04_runs.md`, `05_next_steps.md`
- **6.2 Финальный отчёт**
  - PDF + Notion: единый нарратив и единый набор инфографик
- **6.3 Промпты для агентов**
  - визуализация: карты/инфографика по сети, ОТ, населению, результатам расчёта
  - программист: автоматизация, скрипты, тесты
  - транспортный моделлер: реалистичность параметров и калибровка

## Инструменты экосистемы MATSim (не изобретать велосипед)

Перед написанием кода проверить, есть ли готовое решение в экосистеме [matsim-org](https://github.com/matsim-org):

| Задача | Готовый инструмент | Что мы делали в Шамалгане | Рекомендация |
|--------|--------------------|---------------------------|--------------|
| OSM → MATSim network | `SupersonicOsmNetworkReader` (MATSim core) | `PrepareShamalganNetwork` — обёртка над тем же reader | Использовать core reader напрямую; lane policy и road profile — наш код, но параметризовать |
| GTFS → transit schedule | [GTFS2MATSim](https://github.com/matsim-org/GTFS2MATSim) (contrib) | `PrepareShamalganTransitFromGtfs` — обёртка над `RunGTFS2MATSim` | Использовать `GTFS2MATSim` напрямую как Maven-зависимость |
| GTFS/HAFAS → schedule + mapping на OSM-сеть | [pt2matsim](https://github.com/matsim-org/pt2matsim) | Не использовали | Рассмотреть для production: маппинг PT-маршрутов на реальную сеть вместо pseudo-network |
| Запуск сценария | `MATSimApplication` (core) + picocli CLI | `RunShamalgan` — ручной парсинг аргументов | Перейти на `MATSimApplication` с `prepareConfig`/`prepareScenario`/`prepareControler` |
| Визуализация результатов | SimWrapper (contrib) | `--simwrapper` флаг | Продолжать использовать; добавить custom dashboard YAML при необходимости |
| Валидация PT расписания | `TransitScheduleValidator` (core) | Использовали | Продолжать; включить в пайплайн как обязательный шаг |
| Population из shapefile/zones | `matsim-code-examples/demandGenerationFromShapefile` | Свой `PopulationFromZones` | Наш алгоритм (length-weighted placement) ценен, но стоит оформить как переиспользуемый модуль |

**Справочные материалы:**
- Книга MATSim (теория + конфигурация): [partOne-latest.pdf](https://matsim.org/files/book/partOne-latest.pdf)
- Полная книга: [The Multi-Agent Transport Simulation MATSim](https://www.ubiquitypress.com/reader/books/pdf/10.5334/baw)
- Примеры кода: [matsim-code-examples](https://github.com/matsim-org/matsim-code-examples)
- Шаблон проекта (pom.xml, структура, .gitignore): [matsim-example-project](https://github.com/matsim-org/matsim-example-project)

**Ключевое из `matsim-example-project`:**
- Новую репу делать как форк/копию `matsim-example-project` (правильный `pom.xml` с MATSim BOM `2025.0`, Maven Wrapper, `.gitignore`, CI)
- Java 21 (`maven.compiler.release=21`)
- Fat JAR через `maven-shade-plugin` с `MATSimGUI` как main class
- Сценарии в `scenarios/<city>/`, входные данные в `original-input-data/<city>/`

## Известные пробелы Шамалгана (учесть для следующего города)

- **Кордонный спрос:** Шамалган — закрытая система без внешнего спроса. Для Каскелена (и любого города с существенной маятниковой миграцией) необходимо моделировать кордонные потоки — иначе доли режимов и нагрузка сети будут занижены.
- **Facilities:** нет объектов притяжения — спрос упрощён до `home-work-home` / `home-other-home`. Для production-сценария стоит добавить facilities (магазины, школы, больницы) и соответствующие типы активностей.
- **Route-specific хаки в Java-коде:** blocked origids, mandatory corridors, headway overrides — всё было hardcoded. Вынести в конфигурационные файлы (`pt_route_overrides.json`, `pt_service_profile.csv`).

## Минимальный Definition of Done для нового города (v0 / proof-of-concept)

- **`.gitignore`:** output-файлы не попадают в git.
- **Сеть:** связна; QC отчёт есть; `lanes/speed/capacity` выглядят правдоподобно.
- **Население:** зоны по плотности; `population.xml`; карта распределения активностей по сети.
- **ОТ:** остановки+маршруты+расписание; QA привязки; карта маршрутов. `TransitScheduleValidator` без ошибок.
- **Запуск:** smoke-run (10 итераций) и full-run (100 итераций) с `--simwrapper`, каждый в отдельную папку `output_<tag>`.
- **Анализ:** сходимость score, доли режимов, stuck agents — всё задокументировано.
- **Док:** один отчёт с выводами и списком доработок.
- **Код:** параметризован по городу; route-специфичные данные в CSV/JSON, не в Java.