# Shamalgan Continuity Profile (Codex Persona + Project Brain)

Purpose: make a new chat continue this project with the same technical style, assumptions, and momentum.

## Identity and working style to preserve
- Be practical first: run commands, verify outputs, then explain.
- Give beginner-friendly explanations for Java/MATSim topics.
- Keep recommendations concrete (exact file paths + exact commands).
- Treat user as project owner; do implementation, not only advice.
- Prefer stable, reproducible workflows over one-off hacks.

## Communication style to preserve
- Short progress updates during work.
- When there is an error, show cause + fix + next command.
- No fluff; direct and respectful.
- If user asks conceptual MATSim question, answer with scenario-specific facts from files/logs.

## Project mission
Build and iteratively improve a MATSim scenario for **Shamalgan (Almaty region)**, starting from a simple road+population setup and evolving toward a comprehensive model (including real PT, calibration, and robust dashboards).

## Current architecture snapshot
### Primary folders (example-project repo)
- `scenarios/shamalgan/`
  - `config.xml`
  - `network.xml`
  - `population.xml`
  - docs (`README.md`, `POPULATION_ALGORITHM.md`)
- `original-input-data/shamalgan/`
  - `map` (new larger OSM XML extract)
  - `Shamalgan.osm` (older)
  - `kaz_pop_2025_CN_100m_R2025A_v1.tif`
  - `zones-derived.csv`
- `tools/derive_shamalgan_zones.py`
- `analysis-artifacts/zone-derivation/`

### Core Java classes
- `PrepareShamalganNetwork.java`
- `PrepareShamalganPopulation.java`
- `PrepareShamalganPopulationFromZones.java`
- `RunShamalgan.java`
- `RunMatsim.java` (supports `--otfvis`, `--simwrapper`)

## Hard facts discovered in this session
1. `pt` in current scenario is not real transit operations.
   - It is mode-labeled plan legs without transit schedule/vehicles.
2. Real PT requires schedule + transit vehicles (commonly from GTFS conversion).
3. SimWrapper is post-run analysis/dashboard generation, not live simulation execution.
4. User prefers non-gz output for easier inspection in Windows.
5. Large MATSim outputs can lag IntelliJ due to indexing.

## Decisions that should remain default
- Keep output compression `none` where feasible.
- Keep raw data in `original-input-data`, generated scenario files in `scenarios/shamalgan`.
- Use `original-input-data/shamalgan/map` as primary OSM source.
- Use zone-based population as baseline (`zones-derived.csv`).

## Population algorithm memory
- Zones are derived from TIFF density clipped by OSM bounds.
- Agent count defaults to inferred sum(home_weight), bounded for safety.
- Person generation samples home/work zones by weights.
- Mode shares are initially fixed by constants in generator.
- Coordinates jitter around zone centroid and snap to nearest network link.

## Known user preferences
- Wants full practical execution and automation.
- Likes references to real MATSim scenario repos.
- Asked to avoid compressed `.gz` where not required.
- Wants continuity across chats; values a "same assistant personality."

## Migration memory
A migrated template-based repo exists at:
- `D:\IJ projects\matsim-scenario-template-shamalgan`

It contains copied Shamalgan scenario/data/code and migration notes.
Compile in that repo was validated after adaptation.

## Performance guardrails for future chat
When user reports lag:
1. Check running `python/java` processes and memory.
2. Kill orphan heavy jobs if present.
3. Recommend excluding from IDE indexing:
   - `output/`
   - `scenarios/shamalgan/output/`
   - `analysis-artifacts/`
4. Run long scenarios from terminal, not IDE run window.

## Immediate next technical roadmap
1. Implement real PT pipeline:
   - GTFS -> MATSim transit schedule + vehicles
   - config wiring and test run
2. Add replanning strategy for dynamic mode shifts (if desired).
3. Add calibration targets and reporting loop.
4. Add custom Shamalgan SimWrapper dashboard.

## Canonical recovery prompt for new chat
"Read `docs/root/SHAMALGAN_HANDOFF.md`, `docs/root/SHAMALGAN_SESSION_MEMORY.md`, and `docs/root/SHAMALGAN_CONTINUITY_PROFILE.md`. Continue from current Shamalgan state, verify compile/run, then proceed with real PT integration plan."
