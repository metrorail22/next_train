#!/usr/bin/env python3
"""
convert_gtfs_to_xml.py

Convert a GTFS zip (google_transit.zip) into one XML file that contains:
- agency (if present)
- routes
- stops
- trips
- stop_times (all schedules)
- services from calendar_dates (and calendar if present)

Usage:
	python3 convert_gtfs_to_xml.py
	python3 convert_gtfs_to_xml.py "google_transit.zip" "output.xml"

Notes about service dates:
- If calendar.txt exists, we include it + calendar_dates exceptions.
- If calendar.txt does NOT exist (like your file), we can only list dates found in calendar_dates.txt.
"""

import argparse
import csv
import datetime as dt
import os
import sys
import zipfile
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, ElementTree

def _read_gtfs_csv_from_zip(zf: zipfile.ZipFile, name: str):
	"""Return list of dict rows from a GTFS .txt inside the zip."""
	try:
		with zf.open(name) as f:
			# GTFS is UTF-8 usually; fall back to latin-1 if needed.
			raw = f.read()
	except KeyError:
		return None

	for enc in ("utf-8-sig", "utf-8", "latin-1"):
		try:
			text = raw.decode(enc)
			break
		except UnicodeDecodeError:
			text = None
	if text is None:
		raise RuntimeError(f"Could not decode {name} as utf-8 or latin-1")

	reader = csv.DictReader(text.splitlines())
	return list(reader)

def _safe_attr(elem: Element, key: str, val):
	if val is None:
		return
	s = str(val)
	# Avoid putting "None" or blank strings.
	if s.strip() == "":
		return
	elem.set(key, s)

def _iso_from_yyyymmdd(yyyymmdd: str) -> str:
	try:
		d = dt.datetime.strptime(yyyymmdd, "%Y%m%d").date()
		return d.isoformat()
	except Exception:
		return ""

def build_xml(gtfs_zip_path: str) -> Element:
	with zipfile.ZipFile(gtfs_zip_path, "r") as zf:
		agency = _read_gtfs_csv_from_zip(zf, "agency.txt") or []
		routes = _read_gtfs_csv_from_zip(zf, "routes.txt") or []
		stops = _read_gtfs_csv_from_zip(zf, "stops.txt") or []
		trips = _read_gtfs_csv_from_zip(zf, "trips.txt") or []
		stop_times = _read_gtfs_csv_from_zip(zf, "stop_times.txt") or []
		calendar = _read_gtfs_csv_from_zip(zf, "calendar.txt")  # may be None
		calendar_dates = _read_gtfs_csv_from_zip(zf, "calendar_dates.txt") or []

	now = dt.datetime.now().replace(microsecond=0).isoformat()
	root = Element("gtfs_export")
	root.set("generated_at", now)

	# ---- Agencies ----
	agencies_el = SubElement(root, "agencies")
	for a in agency:
		a_el = SubElement(agencies_el, "agency")
		# Keep all fields as attributes
		for k, v in a.items():
			_safe_attr(a_el, k, v)

	# ---- Routes ----
	routes_el = SubElement(root, "routes")
	for r in routes:
		r_el = SubElement(routes_el, "route")
		for k, v in r.items():
			_safe_attr(r_el, k, v)

	# ---- Stops ----
	stops_el = SubElement(root, "stops")
	for s in stops:
		s_el = SubElement(stops_el, "stop")
		for k, v in s.items():
			_safe_attr(s_el, k, v)

	# ---- Services ----
	services_el = SubElement(root, "services")

	# calendar.txt (weekly patterns)
	if calendar:
		cal_el = SubElement(services_el, "calendar")
		for row in calendar:
			svc_el = SubElement(cal_el, "service")
			for k, v in row.items():
				if k in ("start_date", "end_date"):
					_safe_attr(svc_el, k, v)
					iso = _iso_from_yyyymmdd(v)
					if iso:
						_safe_attr(svc_el, k + "_iso", iso)
				else:
					_safe_attr(svc_el, k, v)

	# calendar_dates.txt (exceptions / explicit dates)
	caldates_el = SubElement(services_el, "calendar_dates")
	# service_id -> list of (date, exception_type)
	svc_dates = defaultdict(list)
	for row in calendar_dates:
		service_id = row.get("service_id", "")
		date = row.get("date", "")
		ex = row.get("exception_type", "")
		svc_dates[service_id].append((date, ex))

	for service_id, items in sorted(svc_dates.items(), key=lambda x: x[0]):
		svc_el = SubElement(caldates_el, "service")
		_safe_attr(svc_el, "service_id", service_id)
		# Sort by date
		items_sorted = sorted(items, key=lambda t: t[0])
		for date, ex in items_sorted:
			d_el = SubElement(svc_el, "date")
			_safe_attr(d_el, "yyyymmdd", date)
			iso = _iso_from_yyyymmdd(date)
			if iso:
				_safe_attr(d_el, "iso", iso)
			_safe_attr(d_el, "exception_type", ex)

	# ---- Trips + Stop times (the schedules) ----
	# Group stop_times by trip_id
	st_by_trip = defaultdict(list)
	for st in stop_times:
		trip_id = st.get("trip_id", "")
		st_by_trip[trip_id].append(st)

	# Sort each trip's stop_times by stop_sequence if present
	def seq_key(st_row):
		v = st_row.get("stop_sequence", "")
		try:
			return int(v)
		except Exception:
			return 10**9

	trips_el = SubElement(root, "trips")
	for t in trips:
		trip_id = t.get("trip_id", "")
		t_el = SubElement(trips_el, "trip")
		for k, v in t.items():
			_safe_attr(t_el, k, v)

		sched_el = SubElement(t_el, "stop_times")
		rows = st_by_trip.get(trip_id, [])
		rows_sorted = sorted(rows, key=seq_key)
		for st in rows_sorted:
			st_el = SubElement(sched_el, "stop_time")
			# Keep all stop_time fields
			for k, v in st.items():
				_safe_attr(st_el, k, v)

	return root

def indent(elem: Element, level: int = 0):
	"""In-place pretty indentation for ElementTree (no external deps)."""
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

def get_zip_file_mtimes(zip_path: str) -> list:
	"""Return a list of {name, modified, size} dicts for every entry in the zip."""
	entries = []
	with zipfile.ZipFile(zip_path, "r") as zf:
		for info in zf.infolist():
			y, mo, d, h, mi, s = info.date_time
			try:
				modified = dt.datetime(y, mo, d, h, mi, s).isoformat()
			except ValueError:
				modified = ""
			entries.append({"name": info.filename, "modified": modified, "size": info.file_size})
	return entries


def main():
	script_dir = os.path.dirname(os.path.abspath(__file__))
	default_input_zip = os.path.join(script_dir, "google_transit.zip")
	default_output_xml = os.path.join(script_dir, "rail_feed.xml")

	ap = argparse.ArgumentParser(description="Convert GTFS google_transit.zip to a single XML export.")
	ap.add_argument(
		"input_zip",
		nargs="?",
		default=default_input_zip,
		help="Path to GTFS zip (defaults to google_transit.zip next to this script)",
	)
	ap.add_argument(
		"output_xml",
		nargs="?",
		default=default_output_xml,
		help="Path to output XML file (defaults to rail_feed.xml next to this script)",
	)
	args = ap.parse_args()

	try:
		if not os.path.isfile(args.input_zip):
			raise FileNotFoundError(f"GTFS zip not found: {args.input_zip}")

		root = build_xml(args.input_zip)

		# Embed modification timestamps of files inside the zip
		zip_entries = get_zip_file_mtimes(args.input_zip)
		if zip_entries:
			zip_mtime = dt.datetime.fromtimestamp(os.path.getmtime(args.input_zip)).replace(microsecond=0).isoformat()
			source_el = SubElement(root, "gtfs_source_files")
			source_el.set("zip_path", args.input_zip)
			source_el.set("zip_modified", zip_mtime)
			for entry in zip_entries:
				f_el = SubElement(source_el, "file")
				f_el.set("name", entry["name"])
				f_el.set("modified", entry["modified"])
				f_el.set("size_bytes", str(entry["size"]))
			print(f"     embedded modification times for {len(zip_entries)} file(s) from {args.input_zip}")

		indent(root)
		tree = ElementTree(root)
		tree.write(args.output_xml, encoding="utf-8", xml_declaration=True)
		print(f"OK: wrote {args.output_xml}")
	except Exception as e:
		print(f"ERROR: {e}", file=sys.stderr)
		sys.exit(1)

if __name__ == "__main__":
	main()