# Shamalgan PT Raw Data Intake

Place newly found PT source files here.

## For each source, record:

- source name and URL/app (e.g., 2GIS export, operator PDF, manual survey)
- collection date
- geographic scope
- file format
- license/reuse constraints
- known limitations

## Expected useful files

- stop list with coordinates
- route-stop sequence per direction
- service window/headway or timetable
- route type / vehicle notes

## Next processing step

After data drop, convert to scenario-ready inputs by updating:
- `analysis-artifacts/pt-data/osm_bus_stops.csv` (or replacement file)
- PT generation pipeline in `PrepareShamalganTransitFromAssumptions` or GTFS conversion path
