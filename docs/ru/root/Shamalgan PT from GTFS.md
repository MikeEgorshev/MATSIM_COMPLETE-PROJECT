# Shamalgan PT from GTFS

Переход от текущего базового сценария (авто + метка «pt») к реальным операциям ОТ в MATSim.

**English:** [SHAMALGAN_REAL_PT_INTEGRATION_PLAN](../../en/root/SHAMALGAN_REAL_PT_INTEGRATION_PLAN.md)

## Фаза 0: Базовый прогон (выполнено 2026-02-24)

- `mvnw -DskipTests compile` проходит.
- `RunShamalgan --simwrapper` выполняется до конца.
- В конфиге пока не было расписания/транспорта ОТ.

## Фаза 1: Конвертер GTFS (реализовано)

- Класс `PrepareShamalganTransitFromGtfs`.
- Входы: zip GTFS (WGS84), дорожная сеть, дата обслуживания.
- Выходы: `network-with-pt.xml`, `transitSchedule.xml`, `transitVehicles.xml`.
- Конфиг ОТ: `scenarios/shamalgan/config.xml` (единый конфиг с ОТ).

## Фаза 2: Первый прогон с реальным ОТ

1. Положить GTFS в `original-input-data/shamalgan/gtfs/shamalgan-gtfs.zip`.
2. Запустить конвертер (команда в `scenarios/shamalgan/README.md`).
3. Запуск: `RunShamalgan scenarios/shamalgan/config.xml --simwrapper`.
4. Проверить: в логах загрузка расписания и транспорта, в анализе — ненулевые поездки ОТ.

## Фаза 3: Поведенческая реалистичность

1. Перепланирование выбора режима (сейчас режимы в населении фиксированы).
2. Настройка полезности ОТ и штрафов за пересадки.
3. При необходимости — доработка доступа/высадки.

## Фаза 4: Калибровка и отчётность

1. Сравнение пассажиропотока ОТ с наблюдениями.
2. Сравнение времени в пути по коридорам.
3. Отдельные дашборды SimWrapper по ОТ Шамалгана.
