# Network QC Report: network.xml

## Core Counts
- Nodes: 1,128
- Links: 2,991

## Connectivity
- Weakly connected components: 1
- Largest component nodes: 1,128 (100.00%)
- Links outside largest component: 0
- Dead-end nodes (total degree = 1): 0
- Isolated nodes (in=0,out=0): 0

## Link Attribute Statistics
- Length [m]: min=2.01, p50=104.68, p95=424.22, max=5107.27
- Free speed [m/s]: min=2.78, p50=4.17, p95=8.33, max=22.22
- Capacity [veh/h]: min=300.00, p50=600.00, p95=1000.00, max=4000.00
- Lanes: min=1.00, p50=1.00, p95=1.00, max=2.00

## Allowed Modes (link counts)
- car: 2,991

## Flagged Issues (counts)
- long_link_gt_5000m: 2

## Output Files
- Issues CSV: `shamalgan-road-network-issues.csv`
- Links outside largest component CSV: `shamalgan-road-network-links_outside_lcc.csv`
- Dead-end nodes CSV: `shamalgan-road-network-dead_end_nodes.csv`
- Isolated nodes CSV: `shamalgan-road-network-isolated_nodes.csv`
