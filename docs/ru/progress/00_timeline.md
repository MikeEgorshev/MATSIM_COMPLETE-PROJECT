# Хронология

## 2026-02-25

- Перенесён и стабилизирован путь запуска Шамалгана в репозитории на базе template.
- Добавлен конвейер PT bootstrap (ОТ по допущениям) на основе остановок OSM (GTFS пока недоступен).
- Построены входы с ОТ:
  - `scenarios/shamalgan/network-with-pt.xml`
  - `scenarios/shamalgan/transitSchedule.xml`
  - `scenarios/shamalgan/transitVehicles.xml`
- Исправлен сбой запуска MATSim с ОТ из-за отсутствующих координат активностей в планах.
- Исправлено несовпадение файла расписания в дашборде SimWrapper (`.xml` vs `.xml.gz`) через свой dashboard provider.
- Добавлен скрипт архивации выходов для снижения нагрузки на IDE:
  - `tools/archive_outputs.ps1`
- Добавлены инструменты и отчёты QC сети:
  - `tools/network_qc_report.py`
  - `analysis-artifacts/network-qc/*`
- Добавлены инфографики по полосам и скоростям:
  - `Visualization/network-qc/network_lane_overview.png`
  - `Visualization/network-qc/network_speed_overview.png`
- Реализован профиль состояния дорог в построителе сети.
- Обновлена политика скоростей до явных целевых значений:
  - местные `20 км/ч`
  - коллекторы `30 км/ч`
  - магистрали `45 км/ч`
  - трассы `70 км/ч`
- Пересобраны сеть и входы ОТ с обновлённой базой.
- Выполнен прогон с ОТ и SimWrapper до итерации 10 с корректными выходами.
