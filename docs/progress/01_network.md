# Network Workstream

## Current Status

- Active network file: `scenarios/shamalgan/network.xml`
- Topology QA: clean
  - single connected component
  - no isolated/dead-end artifacts
- Long connector links (>5 km): 2 links, interpreted as inter-town connectors.

## Lane Policy

- Model interpretation uses lanes per directed MATSim link.
- Applied policy:
  - town/local links: `1 lane per link`
  - highway-level links: `2 lanes per link`
- OSM lane tags are sparse in local classes; defaults are required.

## Speed/Capacity Policy

- Implemented in:
  - `src/main/java/org/matsim/project/PrepareShamalganNetwork.java`
- Poor-road profile now uses explicit target free-speeds:
  - local `20 km/h`
  - collector `30 km/h`
  - arterial `45 km/h`
  - highway `70 km/h`

## Key Outputs

- QC reports:
  - `analysis-artifacts/network-qc/shamalgan-road-network.md`
  - `analysis-artifacts/network-qc/shamalgan-road-network-poor-profile.md`
- Visual diagnostics:
  - `analysis-artifacts/network-qc/network_lane_overview.png`
  - `analysis-artifacts/network-qc/network_speed_overview.png`
