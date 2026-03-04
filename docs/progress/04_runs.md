# Run Log

## Latest PT Run

- Config: `scenarios/shamalgan/config-pt.xml`
- Output: `output/`
- Iterations: `0..10`
- Status: completed successfully

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

## Interpretation

- Run behavior is stable.
- PT is used but remains secondary versus car/walk under current assumptions.
