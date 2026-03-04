# README_RUNNING

Living log of project moves, decisions, and outcomes.

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
  - `docs/root/README_RUNNING.md` must be updated after every exchange.
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
- Added `docs/root/NEW_PC_SETUP.md` with full dependency/install/run requirements for a clean machine.
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

---

## Update Rule
- Append one dated entry per major working session.
- Keep entries short and decision-focused.
