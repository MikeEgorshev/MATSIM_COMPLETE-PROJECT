# Shamalgan Handoff

Use this file to bootstrap a new chat session quickly.

## Current status
- Migrated Shamalgan work into template-based repo:
  - `D:\IJ projects\matsim-scenario-template-shamalgan`
- Compile in migrated template repo already passes (`mvnw -DskipTests compile`).
- Main run class in migrated repo is set to:
  - `org.matsim.project.RunShamalgan`

## Migrated content
- `scenarios/shamalgan/*`
- `original-input-data/shamalgan/*`
- `src/main/java/org/matsim/project/*`
- `tools/derive_shamalgan_zones.py`
- `analysis-artifacts/zone-derivation/*`

## Important docs
- `scenarios/shamalgan/README.md`
- `scenarios/shamalgan/POPULATION_ALGORITHM.md`
- `README_SHAMALGAN.md` (in migrated template repo)

## Known modeling facts
- Current `pt` in Shamalgan is mode-labeled only (no transit schedule/vehicles yet).
- Real PT requires transit schedule + transit vehicles (typically from GTFS conversion).
- SimWrapper outputs are generated after run in `output/` (`dashboard-*.yaml` + `analysis/`).

## Quick commands (migrated template repo)
```powershell
.\mvnw.cmd -q -DskipTests compile
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643"
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganPopulationFromZones" "-Dexec.args=scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml"
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=--simwrapper"
```

## If performance lags
- Exclude `output/`, `scenarios/shamalgan/output/`, `analysis-artifacts/` from IntelliJ indexing.
- Do long runs from terminal instead of IDE run window.

## Suggested next steps
1. Add true transit (GTFS -> MATSim schedule/vehicles).
2. Add mode-choice replanning if dynamic mode shares are desired.
3. Add custom SimWrapper dashboard for Shamalgan KPIs.
