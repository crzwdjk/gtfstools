#!/usr/bin/python3
# timetable.py - print a timetable from GTFS data
# USAGE:
#    timetable.py gtfs.db ROUTE_NUM
#    timetable.py gtfs.db --list

import sqlite3, sys
import triptools

# round up v to a multiple of "to"
def roundup(v, to):
    return ((v + to - 1) // to) * to

# pad string s to length "to" with spaces
def pad_to(s, to):
    return s + " " * (to - len(s))

# get the list of (route_id, route_short_name, route_long_name) that are
# available on the given date
def get_routes(db, date):
    c = db.cursor()
    c.execute("SELECT DISTINCT route_id, route_short_name, route_long_name "
              "FROM routes JOIN trips USING (route_id) JOIN calendar USING (service_id) "
              "WHERE start_date <= ? AND ? <= end_date", (date, date))
    routes = c.fetchall()
    c.close()
    return routes

# return a sorting key for a route number. Route numbers are broken down
# into a prefix, numeric part, and suffix, in that order of significance
# with the numeric part sorted numerically and the rest alphabetically.
def route_key(rt):
    # find the int part
    r = rt[1]
    s = 0
    while s < len(r) and (r[s] < '0' or r[s] > '9'):
        s += 1
    e = s
    while e < len(r) and (r[e] >= '0' and r[e] <= '9'):
        e += 1
    intpart = int(r[s:e]) if s != e else 0
    return (r[0:s], intpart, r[e:])

# ye olde reduce() function of functional programming
def reduce(func, acc, l):
    for item in l:
        acc = func(acc, item)
    return acc

def stop_order_helper(trips, order):
    deferred = set()
    for trip in trips:
        stops = [ st[0] for st in trip ]
        matched = False
        for i, stop in enumerate(stops):
            if stop in order:
                # if this is the first stop we've matched, stick all the
                # preceding stops in the trip right here in the order
                if matched is False:
                    m = order.index(stop)
                    order[m:m] = stops[0:i]
                matched = order.index(stop)
                continue
            # figure out where this stop goes in the order.
            elif matched:
                # stick it in the order
                matched += 1
                order[matched:matched] = [stop]
        if not matched:
            deferred.add(trip)
    return deferred

# return the order of stops for this list of trips
def stop_order(trips):
    longest = reduce(lambda a, l: a if len(a) > len(l) else l, [], trips)
    order = [ st[0] for st in longest ]
    deferred = stop_order_helper(trips, order)
    if deferred:
        raise Exception("TODO: Deferred list is nonempty!")
    return order


# Get the stop names for each of the stop_ids given.
def get_stop_names(db, stop_ids):
    ret = {}
    c = db.cursor()
    for stop_id in stop_ids:
        c = c.execute("SELECT stop_name FROM stops WHERE stop_id = ?",
                      (stop_id,))
        ret[stop_id] = c.fetchone()[0]
    return ret

# format the time string. Currently, converts the seconds
# time into a symbol based on quartar minutes: nothing for
# the first quarter minute, "-" for the second, "+" for the third
# and "*" for the fourth.
def format_time(time):
    (h, m, s) = time.split(":")
    if "00" <= s < "15":
        x = ""
    elif "15" <= s < "30":
        x = "-"
    elif "30" <= s < "45":
        x = "+"
    else:
        x = "*"
    return h + ":" + m + x

daynames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# format the "days" tuple into a string.
def format_days(days):
    if all(days):
        return "DAILY"
    if days == (1, 1, 1, 1, 1, 0, 0):
        return "WEEKDAYS"
    if days == (0, 0, 0, 0, 0, 1, 1):
        return "WEEKENDS"
    return ", ".join([daynames[i] for i, day in enumerate(days) if day])

# print the list of routes in this db
def print_routes(routes):
    routes.sort(key = route_key)
    for rid, short_name, long_name in routes:
        print(pad_to(short_name, 8) + "  " + long_name + "  (" + rid + ")")

# print a timetable with stops on the left, trips going down.
# Takes the trips for one set of days and one direction only.
def print_tt_trips_down(db, route_short_name, route_long_name, days, direction):
    print("%s: %s (%s)" % (route_short_name, route_long_name,
                           format_days(days)))
    for trips in direction:
        stops = triptools.trip_stops(trips)
        stop_name_map = get_stop_names(db, stops)
        trips = triptools.tsort(trips)
        stop_ids = stop_order(trips)
        max_len = max(map(len, stop_name_map.values()))
        target_len = roundup(max_len + 1, 8)
        page_width = 100
        trips_per_page = (page_width - target_len) // 8
        for i in range(0, len(trips), trips_per_page):
            for stop_id in stop_ids:
                if stop_id == '7':
                    raise Exception("WTF!")
                out = pad_to(stop_name_map[stop_id], target_len)
                for trip in trips[i:i + trips_per_page]:
                    t = "-"
                    for st, time in trip:
                        if st == stop_id:
                            t = format_time(time)
                            break
                    out += pad_to(t, 8)
                print(out)
            print()


def main():
    if len(sys.argv) != 3:
        usage()
        return
    dbfile = sys.argv[1]
    db = sqlite3.connect(dbfile)
    date = db.execute("SELECT max(end_date) FROM calendar").fetchone()[0]

    print("Date ", date)
    if sys.argv[2] == "--list":
        routes = get_routes(db, date)
        print_routes(routes)
    else:
        route_short_name = sys.argv[2]
        c = db.execute("""SELECT DISTINCT route_id, route_long_name
                          FROM routes JOIN trips USING (route_id)
                                      JOIN calendar USING (service_id)
                          WHERE route_short_name = ? AND start_date <= ? AND ? <= end_date""",
                          (route_short_name, date, date))
        l = c.fetchall()
        if len(l) < 1:
            c = db.execute("""SELECT DISTINCT route_id, route_long_name
                          FROM routes JOIN trips USING (route_id)
                                      JOIN calendar USING (service_id)
                          WHERE route_id = ? AND start_date <= ? AND ? <= end_date""",
                          (route_short_name, date, date))
            l = c.fetchall()
            if len(l) < 1:
                print("Route not found: ", route_short_name)
                sys.exit(1)
        elif len(l) > 1:
            print("Ambiguous route name: ", route_short_name)
            sys.exit(1)
        (route_id, route_long_name) = l[0]
        t = triptools.route_trips(db, route_id, date)
        for days, direction in t.items():
            print_tt_trips_down(db, route_short_name, route_long_name,
                                days, direction)
    db.close()

if __name__ == "__main__":
    main()
