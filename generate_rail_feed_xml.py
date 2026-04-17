#!/usr/bin/env python3
"""
generate_rail_feed_xml.py

Generate a rail_feed.xml file for the next_trains.php application.
This creates a sample XML structure with stops, services, and trips.

Usage:
  python3 generate_rail_feed_xml.py

Output:
  Creates rail_feed.xml in the same directory
"""

import datetime as dt
import os
import zipfile
from xml.etree.ElementTree import Element, SubElement, ElementTree

def get_zip_file_mtimes(zip_path: str) -> list[dict]:
    """Return a list of {name, modified} dicts for every entry in the zip."""
    entries = []
    if not os.path.isfile(zip_path):
        return entries
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            y, mo, d, h, mi, s = info.date_time
            try:
                modified = dt.datetime(y, mo, d, h, mi, s).isoformat()
            except ValueError:
                modified = ""
            entries.append({"name": info.filename, "modified": modified, "size": info.file_size})
    return entries


def create_sample_rail_feed_xml():
    """Create a sample rail_feed.xml with basic structure."""

    now = dt.datetime.now().replace(microsecond=0)
    root = Element("gtfs_export")
    root.set("generated_at", now.isoformat())

    # ---- Stops ----
    stops_el = SubElement(root, "stops")

    # Sample stops based on the config.php station list
    stations = [
        ("University", "UNIV", "University Station"),
        ("LaSalle", "LASL", "LaSalle Station"),
        ("Amherst", "AMHS", "Amherst Station"),
        ("Humboldt Hospital", "HUMB", "Humboldt Station"),
        ("Utica", "UTIC", "Utica Station"),
        ("Summer-Best", "SUMB", "Summer-Best Station"),
        ("Allen Medical", "ALLN", "Allen-Medical Campus Station"),
        ("Fountain Plaza", "FTPL", "Fountain Plaza Station"),
        ("Lafayette", "LAFA", "Lafayette Station"),
        ("Church St", "CHUR", "Church St Station"),
        ("Seneca", "SENE", "Seneca Station - Merchants Insurance"),
        ("Canalside", "CANL", "Canalside Station"),
        ("DL&W", "DLW", "DL&W Station"),
    ]

    for stop_name, stop_code, full_name in stations:
        stop_el = SubElement(stops_el, "stop")
        stop_el.set("stop_id", f"stop_{stop_code.lower()}")
        stop_el.set("stop_code", stop_code)
        stop_el.set("stop_name", full_name)

    # ---- Services ----
    services_el = SubElement(root, "services")

    # Calendar (weekly patterns)
    calendar_el = SubElement(services_el, "calendar")

    # Weekday service
    weekday_svc = SubElement(calendar_el, "service")
    weekday_svc.set("service_id", "weekday_service")
    weekday_svc.set("monday", "1")
    weekday_svc.set("tuesday", "1")
    weekday_svc.set("wednesday", "1")
    weekday_svc.set("thursday", "1")
    weekday_svc.set("friday", "1")
    weekday_svc.set("saturday", "0")
    weekday_svc.set("sunday", "0")

    # Use current year range so the feed stays valid year-to-year.
    year_str = now.strftime("%Y")
    next_year_str = str(int(year_str) + 1)

    weekday_svc.set("start_date", f"{year_str}0101")
    weekday_svc.set("end_date", f"{next_year_str}1231")

    # Weekend service
    weekend_svc = SubElement(calendar_el, "service")
    weekend_svc.set("service_id", "weekend_service")
    weekend_svc.set("monday", "0")
    weekend_svc.set("tuesday", "0")
    weekend_svc.set("wednesday", "0")
    weekend_svc.set("thursday", "0")
    weekend_svc.set("friday", "0")
    weekend_svc.set("saturday", "1")
    weekend_svc.set("sunday", "1")
    weekend_svc.set("start_date", f"{year_str}0101")
    weekend_svc.set("end_date", f"{next_year_str}1231")

    # Calendar dates (exceptions)
    caldates_el = SubElement(services_el, "calendar_dates")

    # Add some exceptions for holidays, etc.
    # For now, just include the regular services

    # ---- Trips ----
    trips_el = SubElement(root, "trips")

    # Create sample trips for each direction
    trip_counter = 1

    # Get current time in seconds since midnight
    now = dt.datetime.now()
    current_seconds = now.hour * 3600 + now.minute * 60 + now.second

    # Northbound trips (direction_id = "0")
    for hour in range(6, 23):  # 6 AM to 10 PM
        for minute in [0, 15, 30, 45]:  # Every 15 minutes
            if hour == 22 and minute > 0:  # Stop at 10 PM
                continue

            # Only include trips that haven't departed yet today
            trip_seconds = hour * 3600 + minute * 60
            if trip_seconds < current_seconds:
                continue

            trip_id = f"north_{trip_counter:03d}"
            trip_el = SubElement(trips_el, "trip")
            trip_el.set("trip_id", trip_id)
            trip_el.set("route_id", "metro_rail")
            trip_el.set("service_id", "weekday_service")
            trip_el.set("trip_headsign", "Northbound to University")
            trip_el.set("direction_id", "0")

            # Stop times for this trip
            sched_el = SubElement(trip_el, "stop_times")

            # Add stop times for each station (simplified - just arrival/departure at each stop)
            base_time = hour * 3600 + minute * 60  # seconds since midnight

            for i, (stop_name, stop_code, full_name) in enumerate(stations):
                # Each stop takes about 2 minutes
                stop_time = base_time + (i * 120)

                hours = stop_time // 3600
                minutes = (stop_time % 3600) // 60
                seconds = stop_time % 60

                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                st_el = SubElement(sched_el, "stop_time")
                st_el.set("trip_id", trip_id)
                st_el.set("stop_id", f"stop_{stop_code.lower()}")
                st_el.set("arrival_time", time_str)
                st_el.set("departure_time", time_str)
                st_el.set("stop_sequence", str(i + 1))

            trip_counter += 1

    # Southbound trips (direction_id = "1") - similar logic
    for hour in range(6, 23):
        for minute in [0, 15, 30, 45]:
            if hour == 22 and minute > 0:
                continue

            # Only include trips that haven't departed yet today
            trip_seconds = hour * 3600 + minute * 60
            if trip_seconds < current_seconds:
                continue

            trip_id = f"south_{trip_counter:03d}"
            trip_el = SubElement(trips_el, "trip")
            trip_el.set("trip_id", trip_id)
            trip_el.set("route_id", "metro_rail")
            trip_el.set("service_id", "weekday_service")
            trip_el.set("trip_headsign", "Southbound to Canalside")
            trip_el.set("direction_id", "1")

            sched_el = SubElement(trip_el, "stop_times")

            # Reverse the stations for southbound
            for i, (stop_name, stop_code, full_name) in enumerate(reversed(stations)):
                # Each stop takes about 2 minutes
                stop_time = base_time + (i * 120)

                hours = stop_time // 3600
                minutes = (stop_time % 3600) // 60
                seconds = stop_time % 60

                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                st_el = SubElement(sched_el, "stop_time")
                st_el.set("trip_id", trip_id)
                st_el.set("stop_id", f"stop_{stop_code.lower()}")
                st_el.set("arrival_time", time_str)
                st_el.set("departure_time", time_str)
                st_el.set("stop_sequence", str(i + 1))

            trip_counter += 1

    return root

def indent(elem, level=0):
    """In-place pretty indentation for ElementTree."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def main():
    try:
        root = create_sample_rail_feed_xml()
        indent(root)
        tree = ElementTree(root)

        # Write to the shared data directory used by the web app.
        output_path = "/srv/occ-dashboard/data/xml/rail_feed.xml"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Embed modification timestamps of files inside google_transit.zip
        zip_path = os.path.join(os.path.dirname(output_path), "google_transit.zip")
        zip_entries = get_zip_file_mtimes(zip_path)
        if zip_entries:
            source_el = SubElement(root, "gtfs_source_files")
            source_el.set("zip_path", zip_path)
            zip_mtime = dt.datetime.fromtimestamp(os.path.getmtime(zip_path)).replace(microsecond=0).isoformat()
            source_el.set("zip_modified", zip_mtime)
            for entry in zip_entries:
                f_el = SubElement(source_el, "file")
                f_el.set("name", entry["name"])
                f_el.set("modified", entry["modified"])
                f_el.set("size_bytes", str(entry["size"]))
            indent(root)  # re-indent after appending new nodes

        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        print(f"OK: wrote {output_path}")
        if zip_entries:
            print(f"     embedded modification times for {len(zip_entries)} file(s) from {zip_path}")
        print("You can now access next_trains.php and it should load the train data.")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())