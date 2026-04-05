# UDS, PT and Population Distribution Analysis: Conclusions and Improvements

## Purpose and scope

Short analysis (1–2 hours) to understand how the **street network (UDS)**, **public transport (PT)** network, and **population (agent) distribution** of the Shamalgan scenario are built and used, and to decide whether the current setup is acceptable or what to improve.

---

## Current architecture of UDS, PT and population

### UDS (street network)

- **Source:** OSM from `original-input-data/shamalgan/map` → `PrepareShamalganNetwork` → `scenarios/shamalgan/network.xml`.
- **Build:** One connected component; car-only links; lane count from OSM road class and `lanes` tag. Free speed and capacity by road class (city ~1 lane, arterials ~2 lanes).
- **Main parameters:** 1,128 nodes, 2,991 links; length 2–5,107 m (median ~105 m); free speed 2.78–22.22 m/s; capacity 300–4,000 veh/h; lanes 1 or 2.

### PT (public transport)

- **Source:** Bootstrap/mockup without GTFS. Stops from `tagged_route_stops.csv` (from `new_map.gpkg`). Schedules from assumptions and `pt_service_profile.csv`.
- **Build:** `PrepareShamalganTransitFromAssumptions`: snap stops to nearest link; route path via Dijkstra; schedule from periods and headways. Outputs: `network-with-pt.xml`, `transitSchedule.xml`, `transitVehicles.xml`.
- **Main parameters:** 4 lines (6, 11, 213, 256), 8 directions, 58 stops; service 06:00–23:00; 522 departures/day; SwissRailRaptor; modes car, pt, walk in SubtourModeChoice.

### Population (agent distribution)

- **Source:** Zone-weighted synthetic population. Zones from `original-input-data/shamalgan/zones-derived.csv` (derived by `tools/derive_shamalgan_zones.py` from a population-density GeoTIFF and OSM map extent, reprojected to EPSG:32643).
- **Generator:** `PrepareShamalganPopulationFromZones` ([PrepareShamalganPopulationFromZones.java](../../src/main/java/org/matsim/project/PrepareShamalganPopulationFromZones.java)). Alternative (non-zonal) generator: `PrepareShamalganPopulation` (random link-based; not used for current scenario).
- **How home/work coordinates are assigned:**
  1. For each agent: pick one **home zone** by weighted random (by `home_weight`), one **work/other zone** by weighted random (by `work_weight`).
  2. Employed share: `EMPLOYED_SHARE` (0.65). Mode draw: car 55%, pt 25%, walk 20% (initial plan only; replanning can change it).
  3. **Local placement:** place activities on road links using length-weighted choice within a fixed-radius window around the zone centroid (currently 300 m) so agents are not all at the same point.
  4. **Snap to network:** `NetworkUtils.getNearestLinkExactly(network, coord)` — each home and work/other activity is placed on the nearest link in `network.xml` (EPSG:32643).
  5. Plan: employed → `home → work → home`; not employed → `home → other → home`. Times: home end 07:00–08:59 (employed) or 10:00–14:59 (other); work end 16:00–18:59; other end 12:00–19:59.
- **Agent count:** If not passed as 4th argument, inferred as `round(sum(home_weight))` clamped to [500, 100000] (current data ~30,481). Override example: `... population.xml 20000`.
- **Documentation:** [scenarios/shamalgan/POPULATION_ALGORITHM.md](../../scenarios/shamalgan/POPULATION_ALGORITHM.md); [docs/en/progress/02_population.md](02_population.md).

---

## Checks performed

- **UDS:** [shamalgan-road-network-report-ru.md](../../analysis-artifacts/network-qc/shamalgan-road-network-report-ru.md) and lane audit re-read. Connectivity: 1 component, 0 dead-ends, 0 isolated nodes. Lane policy matches report.
- **PT:** [OT_SYSTEM_REPORT.md](../../analysis-artifacts/pt-data/OT_SYSTEM_REPORT.md) and [pt_network_interpretation.md](../../analysis-artifacts/pt-data/pt_network_interpretation.md) confirm 4 lines, 8 routes, 58 stops. [pt_route_on_road_summary.md](../../analysis-artifacts/pt-data/pt_route_on_road_summary.md): 0 stops with snap >80 m, 0 unreachable segments. network-with-pt: 18 pt links, 2 components (expected).
- **Config:** Single `scenarios/shamalgan/config.xml` with PT; `network-with-pt.xml`, `transitSchedule.xml`, `transitVehicles.xml`, `useTransit=true`.
- **Population:** Generator `PrepareShamalganPopulationFromZones` matches [POPULATION_ALGORITHM.md](../../scenarios/shamalgan/POPULATION_ALGORITHM.md). Input `zones-derived.csv` has zone_id, home_x, home_y, home_weight, work_x, work_y, work_weight (EPSG:32643). All activities are link-based (snap to network); no facilities file in config. Zone derivation uses 10×8 grid, WORK_SHARE 0.95; outputs and visuals in [analysis-artifacts/zone-derivation/](../../analysis-artifacts/zone-derivation/).

---

## Acceptance criteria for current scenario

**UDS:** One connected component; no critical artifacts; lane/capacity/speed plausible.

**PT:** Route segments reachable on road network; no excessive stop snap; schedule consistent; documented as mockup.

**Population:** (1) Zones cover the scenario area and use a documented coordinate system (EPSG:32643). (2) All agents are placed on the network (nearest link). (3) Method and parameters (employed share, initial mode shares, time windows) are documented.

**Joint:** Run with config to 10+ iterations without failures.

---

## Gap checklist vs UDS, PT and population

From [06_gap_checklist_2026-03-04.md](06_gap_checklist_2026-03-04.md):

| Gap | Relation | Decision | Note |
|-----|-----------|----------|------|
| 1) PT supply mockup | PT | **Accept for now** | Document as bootstrap. |
| 2) No calibration cycle | PT/UDS/population | **Improve (medium)** | Define targets and script later. |
| 3) Demand realism limited | Population | **Accept for now** | Zone-weighted generation is documented; enrich later (car availability, activity purposes). |
| 4) No facilities | — | Out of scope | Not UDS/PT/population. |
| 5) Not MATSimApplication | — | Out of scope | Not UDS/PT/population. |
| 6) Absolute paths in config | Config | **Improve (high)** | Use relative output paths. |
| 7) No Shamalgan run tests | — | Out of scope | Protects run. |
| 8) Data packaging | — | Out of scope | Not UDS/PT/population. |

---

## Conclusions

- **Is the current scenario acceptable for stated goals?** Yes, for testing PT integration, link capacities/speeds, and population distribution on the network; runs to 10+ iterations.
- **Accept as-is:** UDS connectivity and topology; PT route-on-road QA; single config with PT; population: zone-based generation, coordinates in EPSG:32643, snap to network, documented algorithm and parameters.
- **To improve (priority):**
  - **High:** Use relative paths in scenario config.
  - **Medium:** Calibration loop when data exist; optional spot-check of UDS lanes and population distribution (e.g. home link counts) on key corridors.
  - **Low:** Optional: car availability and activity-purpose split in population; infographic of agent distribution by link (from population.xml).

---

## Recommended next steps

1. Replace absolute output paths with relative paths in `scenarios/shamalgan/config.xml`.
2. Add one integration test: run Shamalgan 0–2 iterations on a small sample; check exit code and main outputs.
3. Keep UDS, PT and population as-is; label PT as bootstrap in docs.
4. When observations exist: define calibration targets and repeatable script; document in progress.
5. Optionally: add a small script or tool to plot agent distribution (e.g. home/work link counts) from `population.xml` for an infographic on UDS/coordinates.

---

## Infographic: agent distribution on UDS / coordinate system

- **Existing visuals** for the *zone* distribution (which drives where agents are drawn from before snap):
  - [analysis-artifacts/zone-derivation/01_density_and_zones.png](../../analysis-artifacts/zone-derivation/01_density_and_zones.png) — density and zones.
  - [analysis-artifacts/zone-derivation/04_density_roads_zones_new_map.png](../../analysis-artifacts/zone-derivation/04_density_roads_zones_new_map.png) — density, roads and zones (new map extent).
  - [analysis-artifacts/zone-derivation/06_zone_weight_map.png](../../analysis-artifacts/zone-derivation/06_zone_weight_map.png) — zone weights.
  - [analysis-artifacts/zone-derivation/07_population_capture_curve.png](../../analysis-artifacts/zone-derivation/07_population_capture_curve.png) — population capture by top zones.

Agents are placed by zone weights, then placed on road links using length-weighted choice within a fixed-radius window around the zone centroid (currently 300 m), and snapped/linked to `network.xml` (EPSG:32643). So spatial distribution on the network follows these zone maps. A direct **agent-on-network** infographic (e.g. home link count per link or per zone) can be produced later by parsing `population.xml` and aggregating by link id.

---

## Related documents

- [shamalgan-road-network-report-ru.md](../../analysis-artifacts/network-qc/shamalgan-road-network-report-ru.md) — UDS QC
- [OT_SYSTEM_REPORT.md](../../analysis-artifacts/pt-data/OT_SYSTEM_REPORT.md) — PT system
- [PT_ASSUMPTIONS_AND_VALIDATION.md](../../analysis-artifacts/pt-data/PT_ASSUMPTIONS_AND_VALIDATION.md) — PT assumptions
- [pt_route_on_road_summary.md](../../analysis-artifacts/pt-data/pt_route_on_road_summary.md) — PT route-on-road QA
- [pt_network_interpretation.md](../../analysis-artifacts/pt-data/pt_network_interpretation.md) — Schedule summary
- [shamalgan-network-with-pt.md](../../analysis-artifacts/network-qc/shamalgan-network-with-pt.md) — Network-with-PT QC
- [06_gap_checklist_2026-03-04.md](06_gap_checklist_2026-03-04.md) — Gap checklist
- [POPULATION_ALGORITHM.md](../../scenarios/shamalgan/POPULATION_ALGORITHM.md) — Population algorithm
- [02_population.md](02_population.md) — Population workstream
- [analysis-artifacts/zone-derivation/README.md](../../analysis-artifacts/zone-derivation/README.md) — Zone derivation and visuals
- [Visualization/pt_routes_map.html](../../Visualization/pt_routes_map.html) — PT routes map

---

## Prompts for other agents (optional)

- **Transport modelling:** “Review UDS lane counts and speeds for key corridors; review PT headways and service window; review adequacy of population distribution (zone weights and local placement window) relative to density and network coverage.”
- **Programmer:** “In config, use relative output paths. Add integration test for Shamalgan run. Optionally: add a script that reads population.xml and outputs home/work link counts or a simple map of agent distribution on the network for infographic.”
- **Visualization:** “If needed for the report, add an infographic of agent distribution on the network (e.g. home link counts per link or per zone) using population.xml and network.xml.”
