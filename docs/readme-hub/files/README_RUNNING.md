# README_RUNNING

Living log of project moves, decisions, and outcomes.

## 2026-02-25

### Documentation and Continuity
- Added structured progress pack under `docs/progress/`:
  - timeline, network, population, PT, runs, next steps.
- Goal: keep a readable semantic compression of decisions and outputs.

### PT Bootstrap and Stability
- Built PT from mapped OSM bus stops due missing reliable GTFS.
- Fixed PT run crash caused by missing activity coordinates in plans.
- Fixed SimWrapper PT schedule mismatch (`.xml` vs `.xml.gz`) by adding custom dashboard provider.

### Network Work
- Audited OSM lane tagging and confirmed sparse local lane tags.
- Kept per-direction lane interpretation (MATSim link model).
- Added lane policy in network prep:
  - local/town links ~1 lane per link
  - highway links ~2 lanes per link
- Added road condition speed profile and then corrected to explicit target baseline:
  - local `20 km/h`, collector `30 km/h`, arterial `45 km/h`, highway `70 km/h`.
- Rebuilt `network.xml` and then regenerated PT network/schedule/vehicles from updated road baseline.

### Scenario Runs
- Completed PT-enabled run with SimWrapper through iteration 10.
- Core interpretation:
  - stable convergence
  - PT used but secondary versus car/walk under current assumptions
  - no fatal warnings

### Artifacts Added
- Network QC + reports: `analysis-artifacts/network-qc/`
- Infographics:
  - `analysis-artifacts/network-qc/network_lane_overview.png`
  - `analysis-artifacts/network-qc/network_speed_overview.png`

---

## Update Rule
- Append one dated entry per major working session.
- Keep entries short and decision-focused.
