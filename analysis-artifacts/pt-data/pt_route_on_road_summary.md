# PT Route On-Road QA

- Routes: 4
- Tagged stop rows: 58
- Stops with snap distance > 80 m: 0
- Max snap distance [m]: 20.611
- Unreachable consecutive stop segments: 0

## Interpretation

- `snap_distance_m` checks how far the tagged point is from the snapped road link geometry.
- `reachable=false` means the directed road network has no path from one stop segment to the next.
- PT route drawing in SVG follows road links from this check (not straight lines).
