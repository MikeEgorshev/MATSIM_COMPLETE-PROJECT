# README_RUNNING

Living log of project moves, decisions, and outcomes.

**Also in Russian:** [README_RUNNING](../../ru/root/README_RUNNING.md)

## Operating Rule

- Update this file after every user-assistant exchange.
- Keep entries short, dated, and decision-focused.

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

### Documentation Workflow Update
- Added continuous update requirement:
  - Run log in `docs/en/root/README_RUNNING.md` (and `docs/ru/root/README_RUNNING.md`).
- Added README collector and hub:
  - script: `tools/collect_readmes.ps1`
  - index: `docs/readme-hub/README.md`
  - collected copies: `docs/readme-hub/files/`

### PT Route IDs From Field Hint
- User provided observed route numbers from screenshot: `6`, `11`, `213`, `256`.
- Implemented temporary route-number adaptation while preserving existing assumed corridor geometry:
  - new lines in schedule: `line_6`, `line_11`, `line_213`, `line_256`
  - directions per line: inbound/outbound
- Generated consistent departures and vehicles using provisional headways:
  - `6`: 10 min, `11`: 12 min, `213`: 20 min, `256`: 20 min
- Added tool:
  - `tools/apply_pt_route_numbers.py`
- Updated files:
  - `scenarios/shamalgan/transitSchedule.xml`
  - `scenarios/shamalgan/transitVehicles.xml`
- Regenerated PT map artifact to reflect new line IDs:
  - `analysis-artifacts/pt-data/assumed_pt_network_map.png`
- Added online corroboration notes for route-number presence (2GIS links) in `docs/progress/03_pt.md`.

### Repo Migration Prep (New PC)
- Added `docs/en/root/NEW_PC_SETUP.md` with full dependency/install/run requirements for a clean machine.
- Prepared to publish full project snapshot (including normally ignored outputs) to new repository using Git LFS for files above GitHub size limits.

### Repo Migration Completed
- Switched remote and pushed full snapshot to:
  - `https://github.com/MikeEgorshev/MATSIM_COMPLETE-PROJECT.git`
- Included ignored artifacts by force-add (outputs, target classes, IDE files) per transfer request.
- Added Git LFS tracking for oversized output XML files to satisfy GitHub file size limits.

### New Field Speed Evidence
- User provided updated local knowledge for Shamalgan road speeds:
  - observed mean speed around `35 km/h`
  - observed minimum speed around `25 km/h`
- Next calibration step should align model speed assumptions to this evidence, while distinguishing:
  - network free-speed parameters (model input)
  - realized travel speed in simulation output (model result)

## 2026-03-04

### Gap Review Against MATSim Guidance + Berlin Scenario
- Completed explicit gap assessment comparing current Shamalgan state with:
  - MATSim Book Part One (`partOne-latest.pdf`)
  - `matsim-scenarios/matsim-berlin`
- Added prioritized checklist and implementation roadmap:
  - `docs/progress/06_gap_checklist_2026-03-04.md`
- Key priorities formalized:
  - replace PT bootstrap with validated operational data
  - introduce explicit calibration loop with measurable targets
  - improve demand realism (car availability + richer activity purposes)
  - remove absolute output paths for portability
  - add active Shamalgan integration test baseline

### Phase 1 Implementation Started
- Made scenario config output paths portable (relative):
  - `scenarios/shamalgan/config.xml` -> `output`
  - `scenarios/shamalgan/config-pt.xml` -> `output`
- Labeled assumption PT pipeline explicitly as bootstrap:
  - `scenarios/shamalgan/README.md`
  - `PrepareShamalganTransitFromAssumptions` class comment
- Added active integration test for Shamalgan run path:
  - `src/test/java/org/matsim/project/RunShamalganIntegrationTest.java`
  - test builds a 200-person sampled plans file and runs iterations `0..2`
- Verified with:
  - `.\mvnw.cmd -q -Dtest=RunShamalganIntegrationTest test` (pass)

### Output Folder Consolidation
- Switched PT config output to the unified folder:
  - `scenarios/shamalgan/config-pt.xml` now writes to `output`
- Archived existing run directories:
  - `output` -> `archive-outputs/output-20260304-152923`
  - `output-pt` -> `archive-outputs/output-pt-20260304-152923`
- Created fresh active `output/` folder for next PT runs.

### Documentation Restructure and Cleanup
- Moved all root-level Markdown docs into:
  - `docs/root/` (legacy); primary docs now in `docs/en/root/` and `docs/ru/root/`.
- Added docs index:
  - `docs/README.md`
- Updated run log docs to unified output folder naming:
  - `docs/progress/04_runs.md` now references `output/`.
- Regenerated README hub index/copies:
  - `tools/collect_readmes.ps1`
  - `docs/readme-hub/README.md`

## 2026-03-06

### Test Run Recovery + Stability Fix
- Recovered the last successful smoke-run pattern from `run-threading-check.log`.
- Confirmed the previous `--simwrapper` failure was in shutdown analysis (`CreateAvroNetwork`) due remote DTD timeout.
- Added offline-safe XML parsing default in runner:
  - `src/main/java/org/matsim/project/RunShamalgan.java`
  - sets `matsim.preferLocalDtds=true` unless already provided by JVM property.
- Verification:
  - `.\mvnw.cmd -q -Dtest=RunShamalganIntegrationTest test` passed.
  - Short PT run with SimWrapper (e.g. `lastIteration=0`, `qsim.endTime=30:00:00` to `output/`) passed.
- Operational note:
  - Without `--config:qsim.endTime 30:00:00`, this PT setup can keep `35` vehicles active indefinitely and delay shutdown.

### Output Path Cleanup
- Deleted remaining live `output-pt/` folder from workspace.
- Confirmed active scenario configs write to unified `output/`:
  - `scenarios/shamalgan/config.xml`
  - `scenarios/shamalgan/config-pt.xml`
- Removed legacy `output-pt` skip pattern from:
  - `tools/collect_readmes.ps1`
- Later (repo cleanup): removed temporary test output folders `output-smoke` and `output-smoke-triptest` and all commands that wrote to them; main run output remains `output/`.

### SimWrapper TripAnalysis Workaround (Temporary)
- Ran full PT scenario (`0..10`) with `--simwrapper` and `qsim.endTime=00:30:00`.
- Confirmed core MATSim run is stable; failure was in SimWrapper shutdown post-processing:
  - `ClassCastException: TextColumn cannot be cast to StringColumn`
  - thrown by `org.matsim.application.analysis.population.TripAnalysis`.
- Implemented temporary workaround in `RunShamalgan`:
  - keep SimWrapper enabled,
  - exclude only `TripDashboard` (`TripDashboard` and FQCN form) via `simwrapper.exclude`.
- Registered project dashboard provider through SPI:
  - `src/main/resources/META-INF/services/org.matsim.simwrapper.DashboardProvider`
  - value: `org.matsim.project.ShamalganDashboardProvider`
- Result:
  - no shutdown exception,
  - dashboards still generated except trip dashboard.
- Explicit revert note recorded in:
  - `docs/progress/04_runs.md` (`SimWrapper Temporary Workaround (2026-03-06)` section).

### SimWrapper TripDashboard Re-Enabled (Root Cause Confirmed)
- Reverted the temporary `TripDashboard` exclusion in `RunShamalgan`.
- Root cause was confirmed as runtime setup, not PT network changes:
  - `qsim.endTime=00:30:00` produced empty/near-empty `output_trips.csv`,
  - `TripAnalysis` then crashed on `main_mode` column handling.
- Validation after revert:
  - smoke run (`lastIteration=0`) with `qsim.endTime=30:00:00` and `--simwrapper` passed.
  - full run (`0..10`) with `qsim.endTime=30:00:00` and `--simwrapper` passed.
- Operational guidance:
  - use `qsim.endTime=30:00:00` (or another realistic horizon) for SimWrapper trip analytics.

---

## Update Rule
- Append one dated entry per major working session.
- Keep entries short and decision-focused.
