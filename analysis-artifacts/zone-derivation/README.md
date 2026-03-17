# Shamalgan Zone Derivation

**Визуализации (PNG) перенесены в `Visualization/zone-derivation/`.** Скрипт `tools/derive_shamalgan_zones.py` пишет их туда.

Generated visuals (in Visualization/zone-derivation/):
- `01_density_and_zones.png`
- `02_top_zones_home_weight.png`
- `03_process_flow.png`
- `04_density_roads_zones_new_map.png` (uses `original-input-data/shamalgan/map`)
- `05_zone_selection_process_new_map.png` (top-zone weights + cumulative coverage)
- `06_zone_weight_map.png`
- `07_population_capture_curve.png`

Key stats are in `summary.csv`.
New-map stats are in `summary_new_map.csv`.

Method:
1. Read raster density grid from `kaz_pop_2025_CN_100m_R2025A_v1.tif`.
2. Clip to OSM `<bounds>` (use `original-input-data/shamalgan/map`; or older `Shamalgan.osm` if needed).
3. Aggregate to a regular grid (new map run uses 10x8 candidate cells).
4. Compute weighted centroid and zone weights.
5. Reproject to EPSG:32643 and write `zones-derived.csv`.
