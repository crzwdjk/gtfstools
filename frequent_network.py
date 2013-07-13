#!/usr/bin/python3
# frequent-network.py - try to find the frequent network from GTFS data
#
# USAGE:
#     frequent_network.py [path/to/gtfs.db]
import sqlite3, sys
import triptools

# get the list of (route_id, route_short_name) that are available on
# the given date
def get_routes(db, date):
    c = db.cursor()
    c.execute("SELECT DISTINCT route_id, route_short_name "
              "FROM routes JOIN trips USING (route_id) JOIN calendar USING (service_id) "
              "WHERE start_date <= ? AND ? <= end_date", (date, date))
    routes = c.fetchall()
    c.close()
    return routes

# Does this set of days contain any weekdays?
def has_weekdays(days):
    return days[0] or days[1] or days[2] or days[3] or days[4]

# return the set of stops for which the headways are acceptable
# Acceptable is defined as within "mins", with a fuzzy "variance" metric
# that is the sum of squares of the difference between a headway and the
# benchmark, when the headway is longer than the benchmark. The variance
# limit is set at 15**2 + 25, which allows for one gap of 30 minutes, or
# many small violations.
def acceptable_headways(hdw, mins):
    ret = set()
    for stop, headways in hdw.items():
        variance = sum([max(h - mins, 0) for h in headways])
        if variance < 250:
            ret.add(stop)
    return ret

# return the set of stops for which the span is acceptable, defined as
# starting/ending within 2*gap minutes of the given start/end times
def acceptable_span(trips, start_time, end_time, gap):
    start_ok_stops = set()
    end_ok_stops = set()
    stoplist = triptools.trip_stops(trips)
    for stop in stoplist:
        earliest_time = None
        latest_time = None
        for trip in trips:
            times = [ tm for st, tm in trip if st == stop ]
            if times:
                earliest_time = times[0]
                break
        for trip in trips[::-1]:
            times = [ tm for st, tm in trip if st == stop ]
            if times:
                latest_time = times[0]
                break
        if triptools.timediff(start_time, earliest_time) < gap * 2:
            start_ok_stops.add(stop)
        if triptools.timediff(latest_time, end_time) < gap * 2:
            end_ok_stops.add(stop)
    return start_ok_stops & end_ok_stops

# check whether rt is a frequent route.
# Frequent is defined as running every 15 minutes or better, during
# the hours of 6 am to 9 pm (7 am on Sat, 8 am on Sun).
# This definition is derived from Vancouver, BC's frequent transit map.
def is_frequent(rt):
    days_run = [ sum(days) for days in rt.keys() ]
    if sum(days_run) < 7:
        print("Frequent routes must run 7 days a week")
        return False

    for days, wd_trips in rt.items():
        for trips in wd_trips:
            if has_weekdays(days):
                start_time = "06:00:00"
            elif days[5]:
                start_time = "07:00:00"
            else:
                start_time = "08:00:00"
            end_time = "21:00:00"
            ttrips = triptools.tfilter(triptools.tsort(trips), start_time, end_time)
            if len(ttrips) == 0:
                return False
            print(len(list(ttrips)))
            span_stops = acceptable_span(ttrips, start_time, end_time, 15)
            if len(span_stops) < 2:
                print("route fails span check on days", days)
                return False
            hdw = triptools.headways(ttrips)
            hdw_stops = acceptable_headways(hdw, 15)
            if len(hdw_stops) < 2:
                print("Headway check fail on days ", days)
                return False
            if len(hdw_stops & span_stops) < 2:
                print("Joint route and stops")
                return False
    return True

def main():
    if len(sys.argv) > 1:
        dbfile = sys.argv[1]
    else:
        dbfile = 'gtfs.db'
    db = sqlite3.connect(dbfile)
    date = db.execute("SELECT max(end_date) FROM calendar").fetchone()[0]
    routes = get_routes(db, date)

    for (route, route_name) in routes:
        print("Checking route", route_name)
        rt = triptools.route_trips(db, route, date)
        if is_frequent(rt):
            print(route_name, "WINS!")

    db.close()

if __name__ == "__main__":
    main()
