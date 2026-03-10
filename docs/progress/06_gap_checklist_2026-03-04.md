# Shamalgan Gap Checklist vs MATSim Guidance (2026-03-04)

This checklist compares current Shamalgan state with:
- MATSim Book Part One (`partOne-latest.pdf`, compiled 2025-06-15)
- `matsim-scenarios/matsim-berlin` (main branch snapshot as of 2026-03-04)

## What is already aligned

- Core minimum scenario structure exists:
  - `config` + `network` + `plans` are runnable.
- PT pipeline exists in two variants:
  - GTFS converter (`PrepareShamalganTransitFromGtfs`)
  - assumptions fallback (`PrepareShamalganTransitFromAssumptions`)
- PT run is operational and validated at least through iteration 10.
- Transit router set to `SwissRailRaptor`.
- Output diagnostics and continuity docs are already strong.

## Gaps (ordered by priority)

### 1) High: PT supply is still mostly placeholder, not validated operations

- Current `docs/progress/03_pt.md` confirms OSM-stop + assumption-based supply is still baseline.
- MATSim PT chapter expects realistic schedule + stops + vehicles consistency for operationally meaningful PT behavior.

Impact:
- PT ridership, transfer patterns, and in-vehicle crowding are not reliable enough for policy conclusions.

### 2) High: No explicit calibration loop against observed counts/mode/distance targets

- Current project docs track outputs, but there is no formal iterative calibration script/workflow.
- MATSim book and Berlin practice both rely on repeated calibration loops and measured targets.

Impact:
- Good-looking convergence can still be behaviorally wrong.

### 3) High: Demand realism is limited (simple activity structure + fixed initial shares)

- Population generator currently uses `home/work/other`, fixed employment share, fixed initial mode probabilities.
- This is acceptable for bootstrap, but below typical open-production scenario practice.

Impact:
- Mode/time/purpose response elasticity is constrained; scenario sensitivity may be biased.

### 4) Medium: Facilities and richer activity system are missing from active run path

- Active configs do not load a facilities file.
- Berlin-like scenarios use facilities and richer activity typing to improve destination realism and scoring behavior.

Impact:
- Destination choice realism and activity constraints are weaker than recommended for mature scenarios.

### 5) Medium: Runner architecture is not yet in `MATSimApplication` pattern

- `RunShamalgan` currently loads config directly and forwards to `RunMatsim`.
- Berlin uses `MATSimApplication` for CLI options, sample scaling, standardized prep/post-processing, and easier scenario operations.

Impact:
- Harder to scale reproducible run variants (`--1pct/--3pct/...`) and structured calibration modes.

### 6) Medium: Portability issue from absolute output paths in scenario configs

- `scenarios/shamalgan/config.xml` and `scenarios/shamalgan/config-pt.xml` use absolute Windows output paths.
- MATSim guidance recommends relative paths and portable config usage.

Impact:
- Reproducibility across machines/OS is fragile.

### 7) Medium: Test coverage for Shamalgan run path is effectively absent

- Existing test file is commented and references old Gunma path.
- Berlin has lightweight scenario run tests in CI for fast regression detection.

Impact:
- Refactors can silently break run entry points or config assumptions.

### 8) Low: Data packaging strategy can be cleaner for long-term collaboration

- Repo currently carries heavy artifacts and outputs for migration convenience.
- Berlin keeps large inputs/outputs externally and keeps repo lightweight where practical.

Impact:
- Clone/CI friction and repository bloat over time.

## Prioritized implementation plan

## Phase 1 (Immediate, 1-2 days): Reproducibility guardrails

1. Replace absolute output paths with relative paths in both scenario configs.
2. Add one active integration test for Shamalgan:
   - run 0-2 iterations on a reduced sample
   - assert exit code and core output files.
3. Keep current PT assumption pipeline, but label it as `bootstrap` in docs/config comments.

Deliverable:
- portable configs + passing basic run test.

## Phase 2 (Short, 3-5 days): Better demand and behavior

1. Extend population generation:
   - explicit car availability attribute
   - split non-work activities into at least `education/shopping/leisure`.
2. Enable `considerCarAvailability=true` once attributes are populated.
3. Add a documented scenario variant for small-sample quick runs.

Deliverable:
- improved mode-choice realism and faster calibration iteration loop.

## Phase 3 (Short, 3-7 days): PT data upgrade

1. Prioritize GTFS ingestion or validated route-stop sequences with service windows/headways.
2. Regenerate:
   - `network-with-pt.xml`
   - `transitSchedule.xml`
   - `transitVehicles.xml`
3. Validate schedule consistency and stop-link mapping before run.

Deliverable:
- first data-grounded PT run replacing placeholder operations.

## Phase 4 (Medium, 1-2 weeks): Calibration workflow

1. Define target set and acceptance bands:
   - counts (if available)
   - mode shares
   - trip distance/time distributions
   - corridor travel times.
2. Create repeatable calibration script:
   - run -> extract KPIs -> score gap -> apply next parameter set.
3. Track each calibration cycle in `docs/progress/04_runs.md`.

Deliverable:
- transparent and repeatable calibration process.

## Phase 5 (Medium, optional): Architecture uplift toward Berlin-style operations

1. Introduce `MATSimApplication`-based run class for Shamalgan.
2. Add sample options (`--1pct`, `--3pct`, etc.) and standardized post-processing hooks.
3. Keep existing `RunShamalgan` entry point as compatibility wrapper during transition.

Deliverable:
- cleaner scenario operations and easier long-term maintenance.

## Suggested execution order

1. Phase 1
2. Phase 2 (in parallel with initial Phase 3 data intake)
3. Phase 3
4. Phase 4
5. Phase 5

## Notes on evidence basis

- This checklist is intentionally conservative:
  - It treats current Shamalgan as a strong bootstrap baseline.
  - It flags only gaps that directly affect realism, portability, or reproducibility.
