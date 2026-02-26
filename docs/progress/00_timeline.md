# Timeline

## 2026-02-25

- Migrated and stabilized Shamalgan run path in template repository.
- Added PT bootstrap pipeline from mapped OSM bus stops (no GTFS available yet).
- Built PT-enabled inputs:
  - `scenarios/shamalgan/network-with-pt.xml`
  - `scenarios/shamalgan/transitSchedule.xml`
  - `scenarios/shamalgan/transitVehicles.xml`
- Fixed MATSim PT runtime failure caused by missing activity coordinates in plans.
- Fixed SimWrapper PT dashboard schedule file mismatch (`.xml` vs `.xml.gz`) via project dashboard provider.
- Added output archive script to reduce IDE load:
  - `tools/archive_outputs.ps1`
- Added network QC tooling and reports:
  - `tools/network_qc_report.py`
  - `analysis-artifacts/network-qc/*`
- Added lane and speed overview infographics:
  - `analysis-artifacts/network-qc/network_lane_overview.png`
  - `analysis-artifacts/network-qc/network_speed_overview.png`
- Implemented road-condition profile in network builder.
- Updated speed policy to explicit targets:
  - local `20 km/h`
  - collector `30 km/h`
  - arterial `45 km/h`
  - highway `70 km/h`
- Rebuilt network and PT inputs from updated baseline.
- Completed PT + SimWrapper run through iteration 10 with valid outputs.
