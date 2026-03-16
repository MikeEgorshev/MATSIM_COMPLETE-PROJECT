# Run Log

## Latest PT Run

- Config: `scenarios/shamalgan/config.xml`
- Output: `output/`
- Iterations: `0..10`
- Status: completed successfully

## SimWrapper TripDashboard Status (2026-03-06)

- Root cause of observed `ClassCastException`:
  - run was executed with `qsim.endTime=00:30:00` (30 minutes),
  - this produced empty/near-empty `output_trips.csv`,
  - `TripAnalysis` then failed on `main_mode` column handling.
- Conclusion:
  - not linked to the updated PT network itself.
- Current state:
  - `TripDashboard` exclusion has been reverted.
  - `RunShamalgan` now uses SimWrapper default dashboards (TripDashboard included).
- Verified stable runs:
  - smoke run with `lastIteration=0` and `qsim.endTime=30:00:00` passes.
  - full run `0..10` with `qsim.endTime=30:00:00` and `--simwrapper` passes.
- Practical guidance:
  - for SimWrapper dashboard generation, use `qsim.endTime=30:00:00` (or higher realistic value),
  - avoid `00:30:00` when expecting trip analytics.

## Observed KPIs

From `output/modestats.csv`:
- Iteration 10 shares:
  - car: `0.5243`
  - pt: `0.1394`
  - walk: `0.3363`

From `output/scorestats.csv`:
- `avg_executed` improved from `115.34` (it.0) to `125.996` (it.10)

## Warnings Review

- No fatal errors.
- Non-blocking warnings observed:
  - deprecated routing module notice
  - PT synthetic link storage enlargement notices

## Infinite or multi-day run (PT without endTime)

- **Symptom:** Run does not finish in reasonable time (e.g. runs many days instead of one day).
- **Cause:** With PT enabled, if `qsim.endTime` is not set, the QSim can keep waiting for PT vehicles/agents to "finish"; shutdown is delayed and the run appears to hang.
- **Fix:** `scenarios/shamalgan/config.xml` now sets `<param name="endTime" value="30:00:00" />` in the qsim module so the simulated day ends at 30:00 (6:00 next day) and the run terminates. Do not remove this when running with PT.

## Interpretation

- Run behavior is stable.
- PT is used but remains secondary versus car/walk under current assumptions.
