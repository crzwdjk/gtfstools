gtfstools
=========

Tools for analysis of transit data in GTFS format. Tools include:

* gtfs-parse.py - a parser to convert GTFS data into an SQLite database
  for easier querying.

* timetable.py - a utility to print route timetables from GTFS data,
  in simple text-only format.

* frequent_network.py - a utility to find the "frequent transit network"
  in a transit system described by a GTFS dataset.

Prerequisites
-------------

These tools are written in Python 3. They use sqlite3, which is part
of the Python standard library, and the Spatialite extension that adds
spatial functionality to SQLite.
