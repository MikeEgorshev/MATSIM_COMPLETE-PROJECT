# PT Network Interpretation

Generated: 2026-03-05 12:48:26

## High-level read
- Lines: 4
- Routes: 8
- Physical stops (unique stopAreaId): 58
- Departures per day (from schedule): 522
- Service window: 06:00 to 23:00

## Line summary
| Line | Routes | Physical stops | Loop km | Departures/day | Span | Median headway |
|---|---:|---:|---:|---:|---|---:|
| 6 | 2 | 13 | 16.92 | 72 | 06:00-22:53 | 30.0 min |
| 11 | 2 | 19 | 26.28 | 144 | 06:00-23:00 | 15.0 min |
| 213 | 2 | 21 | 53.52 | 218 | 06:00-22:56 | 10.0 min |
| 256 | 2 | 5 | 9.25 | 88 | 06:00-22:50 | 25.0 min |

## Data-quality checks
- Route link references missing in network: 0
- Route lengths are computed from `route/linkRefId` lengths in `network-with-pt.xml`.
- Physical stops are counted using `stopAreaId` to avoid platform duplicates.

Infographic: `analysis-artifacts\pt-data\pt_network_infographic.png`
