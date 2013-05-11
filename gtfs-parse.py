#!/usr/bin/python3

import sqlite3, csv

schema = """
SELECT load_extension('/usr/lib/libspatialite.so.3');
SELECT InitSpatialMetaData();

CREATE TABLE calendar (service_id VARCHAR PRIMARY KEY,
                       start_date VARCHAR, end_date VARCHAR,
                       monday BOOLEAN, tuesday BOOLEAN, wednesday BOOLEAN,
                       thursday BOOLEAN, friday BOOLEAN, saturday BOOLEAN,
                       sunday BOOLEAN);

CREATE TABLE routes (route_long_name VARCHAR, route_type INTEGER,
                     route_text_color VARCHAR, route_color VARCHAR,
                     agency_id VARCHAR, route_id VARCHAR PRIMARY KEY,
                     route_url VARCHAR, route_desc VARCHAR,
       	             route_short_name VARCHAR);

CREATE TABLE trips (trip_id VARCHAR PRIMARY KEY, block_id VARCHAR,
                    route_id VARCHAR REFERENCES routes(route_id),
                    direction_id VARCHAR, trip_headsign INTEGER,
                    service_id VARCHAR REFERENCES calendar(service_id),
                    shape_id INTEGER);

CREATE INDEX trip_route_idx ON trips (route_id);

CREATE TABLE stops (zone_id INTEGER,
                    stop_id VARCHAR PRIMARY KEY, stop_desc VARCHAR,
                    stop_name VARCHAR, location_type INTEGER,
                    stop_url VARCHAR);

SELECT AddGeometryColumn('stops', 'location', 4326, 'POINT', 'XY');

CREATE TABLE stop_times (trip_id VARCHAR REFERENCES trips(trip_id),
                         arrival_time TIME, departure_time TIME,
                         stop_id VARCHAR REFERENCES stops(stop_id),
                         stop_sequence INTEGER, stop_headsign VARCHAR,
                         pickup_type VARCHAR, drop_off_type VARCHAR,
                         shape_dist_traveled VARCHAR);

CREATE INDEX stop_time_idx ON stop_times (trip_id, stop_sequence);
"""

# standard columns that we currently support in our schema
stdcols = {
    "calendar": ("service_id", "start_date", "end_date",
                 "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    "routes": ("route_long_name", "route_type", "route_text_color", "route_color", "agency_id",
               "route_id", "route_desc", "route_short_name"),
    "trips": ("trip_id", "block_id", "route_id", "direction_id", "trip_headsign",
              "service_id", "shape_id"),
    "stops": ("zone_id", "stop_id", "stop_desc", "stop_name", "location_type", "location"),
    "stop_times": ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence",
                   "stop_headsign", "pickup_type", "drop_off_type", "shape_dist_traveled")
}

# create the tables for the schema
def create_tables(db):
    db.enable_load_extension(True)
    cur = db.cursor()
    db.executescript(schema)

# Try to infer the type of string val. If it can be round-tripped through
# an int representation, it's an int. If it parses as a float, it's a float
def ducktype(val):
    try:
        iv = int(val)
        if str(iv) == val:
            return iv
    except ValueError:
        pass
    try:
        fv = float(val)
        if str(fv) == val:
            return fv
    except ValueError:
        return val

# returns a mapping of table name to filehandle
def open_files():
    files = {}
    files["calendar"] = open("calendar.txt", newline='')
    files["routes"] = open("routes.txt", newline='')
    files["trips"] = open("trips.txt", newline='')
    files["stop_times"] = open("stop_times.txt", newline='')
    files["stops"] = open("stops.txt", newline='')
    return files

# takes a dict files where the keys specify the table names in db,
# and the values are filehandles containing the values (in CSV format)
# that go into that table.
def parse_files(db, files):
    cur = db.cursor()
    for table in files.keys():
        infile = csv.reader(files[table])
        print("Reading " + table)
        cols = next(infile)
        showcols = [col for col in cols if col in stdcols[table]]

        # special case to store stop location in the spatial column
        if table == "stops" and "stop_lat" in cols and "stop_lon" in cols:
            extracols = "location, "
            extravals = "MakePoint(:stop_lat,:stop_lon, 4326), "
        else:
            extracols = extravals = ""

        # assemble query from column names and placeholder names
        colstmt = " (" + extracols + ",".join(showcols) + ")"
        valstmt = " (" + extravals + ",".join([":" + col for col in showcols]) + ")"
        query = "INSERT INTO " + table + colstmt + " VALUES" + valstmt

        try:
            cur.executemany(query, map(lambda line: dict(zip(cols, line)), infile))
        except Exception:
            print(query)
            print(v)
            raise

        db.commit()
    cur.close()

def main():
    db = sqlite3.connect('gtfs.db')
    files = open_files()
    create_tables(db)
    parse_files(db, files)
    db.close()

if __name__ == "__main__":
    main()
