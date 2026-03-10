# Shamalgan Session Memory (Conversation Restore)

This file captures the practical memory of our collaboration so a new chat can continue with minimal loss.
Date context: 2026-02-23.

## 1) User goal and constraints
- Goal: build a MATSim scenario for Shamalgan (Almaty region), starting from matsim-example-project, then migrating into matsim-scenario-template style project.
- User preference: no `.gz` output if not required; easier files to inspect in Windows/IntelliJ.
- User is still learning Java and asked for beginner-friendly docs and code comments/placeholders.
- User needs practical commands, not theory only.

## 2) Major decisions we made
- Keep scenario data in `scenarios/shamalgan` and raw inputs in `original-input-data/shamalgan`.
- Use `SupersonicOsmNetworkReader` for `.pbf` and fallback `OsmNetworkReader` for `.osm` XML.
- Use derived zonal population from TIFF + OSM extent (not only manual constant-pop synthetic generation).
- Keep MATSim compression type set to `none` in config for plain XML outputs.
- Enable optional flags in runner:
  - `--otfvis` (live viewer)
  - `--simwrapper` (post-run dashboards)

## 3) What was implemented in matsim-example-project

### Java classes added/updated
- `src/main/java/org/matsim/project/PrepareShamalganNetwork.java`
  - reads OSM and writes `network.xml`
- `src/main/java/org/matsim/project/PrepareShamalganPopulation.java`
  - basic synthetic population
- `src/main/java/org/matsim/project/PrepareShamalganPopulationFromZones.java`
  - weighted zone-based population
  - supports optional 4th arg `agentCount`
  - if omitted, infers population from sum(home_weight)
- `src/main/java/org/matsim/project/RunShamalgan.java`
  - dedicated run entry point for scenario
- `src/main/java/org/matsim/project/RunMatsim.java`
  - supports `enableOtfvis`, `enableSimwrapper`

### Scenario and docs
- `scenarios/shamalgan/config.xml`
- `scenarios/shamalgan/network.xml`
- `scenarios/shamalgan/population.xml`
- `scenarios/shamalgan/README.md`
- `scenarios/shamalgan/POPULATION_ALGORITHM.md`

### Derivation pipeline and infographics
- `tools/derive_shamalgan_zones.py`
  - takes TIFF density + OSM bounds from `original-input-data/shamalgan/map`
  - outputs `zones-derived.csv` and infographics
- `analysis-artifacts/zone-derivation/*`
  - regenerated 01..07 plots for new map extent

## 4) Data inputs used
- OSM new primary file:
  - `original-input-data/shamalgan/map` (no extension, OSM XML)
- older OSM retained:
  - `original-input-data/shamalgan/Shamalgan.osm`
- TIFF:
  - `original-input-data/shamalgan/kaz_pop_2025_CN_100m_R2025A_v1.tif`

## 5) Population derivation details (agreed logic)
- Clip TIFF by OSM `<bounds>` from `map` file.
- Grid zoning (currently 10x8 candidate cells in Python script).
- For non-empty cells, compute weighted centroid and weights.
- Convert centroids to `EPSG:32643` for MATSim.
- Write `zones-derived.csv` (home/work weights + sigma).
- In Java generator:
  - weighted random sample of home zone and activity zone
  - employed share and mode share from constants
  - random jitter around centroid by sigma
  - snap to nearest network links
  - create plan `home-work-home` or `home-other-home`

## 6) Current numbers/results we observed
- Derived bbox population estimate with new map extent ~ 30,481.
- Population generation created ~30,481 agents.
- Example MATSim run completed (iteration 0..10) successfully.
- Mode split remained flat across iterations (expected with current setup and fixed mode assignment).

## 7) Clarified PT modeling state
- Current `pt` is only a mode label in plans.
- No transit schedule/vehicles loaded in config, so no real bus/train operations.
- Real PT requires transit schedule + transit vehicles (usually GTFS conversion workflow).

## 8) SimWrapper understanding
- SimWrapper does not run the simulation itself.
- It creates dashboards from output data after MATSim run.
- Important: open `output` root in SimWrapper (contains `dashboard-*.yaml` and `simwrapper-config.yaml`), not only `output/analysis`.

## 9) Performance and lag lessons
- Severe lag happened mostly due to memory pressure and occasional orphan python process.
- We killed one stuck python process before (~6.9 GB WS).
- IntelliJ indexing large output files can cause lag.
- Recommended exclusions in IDE:
  - `output/`
  - `scenarios/shamalgan/output/`
  - `analysis-artifacts/`

## 10) Migration to template repo
- Cloned:
  - `D:\IJ projects\matsim-scenario-template-shamalgan`
- Copied Shamalgan scenario/code/data there.
- Added:
  - `docs/root/README_SHAMALGAN.md`
- Adjusted template POM to run Shamalgan path and compile successfully in this environment.

## 11) Important caveat on template
- GitHub template clone currently contains many Gunma-specific classes and newer-version assumptions.
- For local success we adapted build path to focus on `org.matsim.project` (Shamalgan classes) and MATSim version compatible with current environment.
- Treat this as pragmatic migration baseline, not final architecture.

## 12) Open tasks for comprehensive model
1. Add true public transport:
   - GTFS -> MATSim transit schedule + transit vehicles
   - update config transit modules
2. Add dynamic mode choice replanning strategy if desired.
3. Add facilities and possibly land-use based attraction model.
4. Add calibration targets (counts/speeds/mode share/trip length distributions).
5. Build custom Shamalgan SimWrapper dashboards.

## 13) Suggested prompt for new chat
Use this in a new chat:

"Read `docs/root/SHAMALGAN_SESSION_MEMORY.md` and `docs/root/SHAMALGAN_HANDOFF.md`, then continue from the migration state. First verify compile and run `RunShamalgan --simwrapper`, then propose next steps for real PT via GTFS."

## 14) Tone/working agreement memory
- User appreciates practical, hands-on help and direct commands.
- User prefers if assistant runs commands directly when possible.
- User likes referencing real MATSim scenario repos for guidance.
