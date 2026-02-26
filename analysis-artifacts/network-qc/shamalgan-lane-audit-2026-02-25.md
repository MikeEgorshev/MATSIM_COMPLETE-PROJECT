# Shamalgan Lane Audit (2026-02-25)

## Source checks

- OSM source: `original-input-data/shamalgan/map`
- MATSim network: `scenarios/shamalgan/network.xml`

## OSM lane-tag completeness

- Highway ways total: `929`
- Highway ways with `lanes=*`: `43` (~4.6%)

Main classes (tagged subset):
- `trunk`: mostly `lanes=2` (one-way motorway-style segments)
- `primary`: `lanes=2` or `4`
- `secondary`: `lanes=2` or `4`

Local classes:
- `residential`: no lane tags
- `service`: no lane tags
- `unclassified`: almost no lane tags

Interpretation: local lane counts are mostly untagged in OSM, so defaults are required.

## MATSim link lanes (current)

- Total car links: `2991`
- `permlanes=1.0`: `2955`
- `permlanes=2.0`: `36`

By capacity:
- `3000` and `4000` capacity links are all `2.0` lanes
- lower-capacity town links are almost entirely `1.0` lanes

## Policy result

We implemented a lane-policy pass in `PrepareShamalganNetwork` to infer per-direction lanes from OSM road class and lane tags. After regeneration, resulting `network.xml` stayed effectively unchanged, indicating current generated lanes are already consistent with the target rule:

- Town roads: ~`1 lane per link`
- Highway-level roads: ~`2 lanes per link`

## Remaining uncertainty

Because OSM lane tags are sparse for local roads, exact lane realism still depends on defaults and should be spot-checked in Yandex panorama for critical corridors.
