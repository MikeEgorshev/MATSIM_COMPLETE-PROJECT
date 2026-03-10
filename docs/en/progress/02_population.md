# Population Workstream

## Current Status

- Active population file: `scenarios/shamalgan/population.xml`
- Generator path:
  - `src/main/java/org/matsim/project/PrepareShamalganPopulationFromZones.java`
- Zone-weighted generation inputs:
  - `original-input-data/shamalgan/zones-derived.csv`

## Method Notes

- Zone weighting derives home/work attractiveness from density and mapped features.
- Detailed algorithm notes:
  - `scenarios/shamalgan/POPULATION_ALGORITHM.md`

## Open Improvements

- Add explicit heterogeneity:
  - car availability distribution
  - activity-purpose split (work/education/shopping/leisure)
- Validate departure time profiles against local expectations.
