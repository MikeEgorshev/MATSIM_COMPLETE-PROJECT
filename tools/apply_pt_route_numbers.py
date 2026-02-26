#!/usr/bin/env python3
"""
Remap assumed PT schedule into named route numbers based on partial field hints.

Current use-case:
- Preserve existing stop geometry and path (inbound/outbound templates)
- Replace generic line IDs with route numbers: 6, 11, 213, 256
- Generate departures/vehicles per assumed headway

This keeps scenario runnable while real PT stop sequences/timetables are being collected.
"""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "scenarios" / "shamalgan" / "transitSchedule.xml"
VEHICLES = ROOT / "scenarios" / "shamalgan" / "transitVehicles.xml"

# Assumption profile until validated source data is available.
ROUTE_HEADWAYS_SEC = {
    "6": 600,    # 10 min
    "11": 720,   # 12 min
    "213": 1200, # 20 min
    "256": 1200, # 20 min
}
SERVICE_START = 6 * 3600
SERVICE_END = 23 * 3600


def hhmmss(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def clone(elem: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(elem, encoding="utf-8"))


def regenerate_schedule() -> set[str]:
    tree = ET.parse(SCHEDULE)
    root = tree.getroot()

    inbound_tpl = root.find("./transitLine[@id='line_bus_assumed_inbound']/transitRoute[@id='route_inbound']")
    outbound_tpl = root.find("./transitLine[@id='line_bus_assumed_outbound']/transitRoute[@id='route_outbound']")
    if inbound_tpl is None or outbound_tpl is None:
        raise RuntimeError("Could not find inbound/outbound template routes in transitSchedule.xml")

    # Remove old lines.
    for line in list(root.findall("./transitLine")):
        root.remove(line)

    vehicle_ids: set[str] = set()

    for route_no, headway in ROUTE_HEADWAYS_SEC.items():
        line = ET.SubElement(root, "transitLine", {"id": f"line_{route_no}"})

        for direction, template in [("inbound", inbound_tpl), ("outbound", outbound_tpl)]:
            route = clone(template)
            route.set("id", f"route_{route_no}_{direction}")

            dep_container = route.find("./departures")
            if dep_container is None:
                dep_container = ET.SubElement(route, "departures")
            else:
                dep_container.clear()

            idx = 0
            t = SERVICE_START
            while t <= SERVICE_END:
                dep_id = f"dep_{route_no}_{direction}_{idx}"
                veh_id = f"veh_{route_no}_{direction}_{idx}"
                ET.SubElement(
                    dep_container,
                    "departure",
                    {
                        "id": dep_id,
                        "departureTime": hhmmss(t),
                        "vehicleRefId": veh_id,
                    },
                )
                vehicle_ids.add(veh_id)
                idx += 1
                t += headway

            line.append(route)

    # Pretty indentation.
    ET.indent(tree, space="\t")
    xml = ET.tostring(root, encoding="unicode")
    with SCHEDULE.open("w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE transitSchedule SYSTEM "http://www.matsim.org/files/dtd/transitSchedule_v2.dtd">\n\n')
        f.write(xml)
        f.write("\n")

    return vehicle_ids


def regenerate_vehicles(vehicle_ids: set[str]) -> None:
    tree = ET.parse(VEHICLES)
    root = tree.getroot()

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}", 1)[0] + "}"

    # Remove all existing vehicle entries.
    for v in list(root.findall(f"./{ns}vehicle")):
        root.remove(v)

    # Keep existing vehicleType and append fresh vehicle list.
    for vid in sorted(vehicle_ids):
        ET.SubElement(root, f"{ns}vehicle", {"id": vid, "type": "busType_assumed"})

    ET.indent(tree, space="\t")
    tree.write(VEHICLES, encoding="utf-8", xml_declaration=True)


def main() -> None:
    vehicle_ids = regenerate_schedule()
    regenerate_vehicles(vehicle_ids)

    print(f"Updated schedule: {SCHEDULE}")
    print(f"Updated vehicles: {VEHICLES}")
    print("Route/headway assumptions:")
    for k, v in ROUTE_HEADWAYS_SEC.items():
        print(f"  route {k}: {v//60} min")
    print(f"Service window: {hhmmss(SERVICE_START)} - {hhmmss(SERVICE_END)}")
    print(f"Vehicles generated: {len(vehicle_ids)}")


if __name__ == "__main__":
    main()
