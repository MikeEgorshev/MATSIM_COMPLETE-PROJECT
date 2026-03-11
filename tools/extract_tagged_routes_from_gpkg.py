#!/usr/bin/env python3
"""
Extract route-ordered stop assignments from new_map.gpkg into a CSV that
PrepareShamalganTransitFromAssumptions can consume.

Source fields expected in layer New_Points:
- osm_id
- name
- Routes
- route direction    (contains mappings like "6"=>"7","11"=>"15")

Output columns:
- route_id, stop_seq, stop_id, name, x, y
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GPKG = ROOT / "original-input-data" / "shamalgan" / "new_map.gpkg"
OUT = ROOT / "analysis-artifacts" / "pt-data" / "tagged_route_stops.csv"

LAYER = "New_Points"
MAP_PATTERN = re.compile(r'"?(\d+)"?\s*=>\s*"?(\d+)"?')
OGR2OGR = Path(r"C:\Program Files\QGIS 3.36.3\bin\ogr2ogr.exe")
TMP_RAW = ROOT / "analysis-artifacts" / "pt-data" / "_new_points_raw.csv"


def parse_route_map(value: str) -> list[tuple[str, int]]:
    if not value:
        return []
    out: list[tuple[str, int]] = []
    for rid, seq in MAP_PATTERN.findall(value):
        out.append((rid.strip(), int(seq)))
    return out


def main() -> None:
    if not GPKG.exists():
        raise FileNotFoundError(f"Missing {GPKG}")
    if not OGR2OGR.exists():
        raise FileNotFoundError(f"Missing {OGR2OGR}")

    OUT.parent.mkdir(parents=True, exist_ok=True)

    extracted: list[dict[str, object]] = []
    subprocess.run(
        [
            str(OGR2OGR),
            "-f",
            "CSV",
            str(TMP_RAW),
            str(GPKG),
            LAYER,
            "-lco",
            "GEOMETRY=AS_XY",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with TMP_RAW.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            route_map = row.get("route direction", "") or ""
            parsed = parse_route_map(str(route_map))
            if not parsed:
                continue
            x_raw = row.get("X", "")
            y_raw = row.get("Y", "")
            if not x_raw or not y_raw:
                continue
            osm_id = row.get("osm_id", "") or ""
            name = row.get("name", "") or ""
            fid = i
            x = float(x_raw)
            y = float(y_raw)

            # Keep names CSV-friendly for the Java split parser.
            clean_name = str(name).replace(",", " ").strip()
            stop_id_base = str(osm_id).strip() or f"fid_{fid}"
            for route_id, seq in parsed:
                extracted.append(
                    {
                        "route_id": route_id,
                        "stop_seq": seq,
                        "stop_id": f"{route_id}_{stop_id_base}",
                        "name": clean_name or f"stop_{stop_id_base}",
                        "x": float(x),
                        "y": float(y),
                    }
                )

    extracted.sort(key=lambda r: (int(str(r["route_id"])), int(r["stop_seq"])))

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["route_id", "stop_seq", "stop_id", "name", "x", "y"],
        )
        w.writeheader()
        for row in extracted:
            w.writerow(row)

    print(f"Extracted route-stop rows: {len(extracted)}")
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
