# triptools - a set of tools for dealing with "trip" structures.
import routetools


# just perl's cmp operator, needed for sorting
def cmp(a, b):
    if a < b: return -1
    if a == b: return 0
    if a > b: return 1
    raise Exception("WTF!")

# attempt to compare two trips, at the first stop they have in common.
# returns values like cmp(), or None if they can't be compared
def comptrips(a, b):
    for st1 in a:
        for st2 in b:
             if st1[0] == st2[0]:
                return cmp(st1[1], st2[1])
    # couldn't find a stop in common between these two
    return None

# topologically sort a list of trips
# we need a tsort because two trips may not have any stops in common
# and thus may not be directly comparable, but still need to be ordered.
def tsort(trips):
    newtrips = []
    while trips:
        # find the earliest trip
        for i in range(len(trips)):
            is_min = True
            for j in range(len(trips)):
                if comptrips(trips[i], trips[j]) == 1:
                    is_min = False
                    break
            if is_min:
                earliesttrip = trips[i]
                del trips[i]
                break
        newtrips.append(earliesttrip)
    return newtrips

# return the set of stops for this set of trips.
def trip_stops(trips):
    stops = set()
    for trip in trips:
        for st, tm in trip:
            stops.add(st)
    return stops

# parse "HH:MM:SS" into minutes.
def parse_time(t):
    (h, m, s) = map(lambda x: int(x), t.split(":"))
    return h * 60 + m + s / 60.0

# difference between two times (in minutes)
def timediff(t1, t2):
    return parse_time(t2) - parse_time(t1)

def end_after(trip, time):
    return timediff(trip[-1][1], time) <= 0

def start_before(trip, time):
    return timediff(trip[0][1], time) >= 0

# return all trips that end after start_time and start before end_time
def tfilter(trips, start_time, end_time):
    return list(filter(lambda t: end_after(t, start_time) and start_before(t, end_time),
                  trips))

def headways(trips):
    ret = {}
    for stop in trip_stops(trips):
        times = []
        for trip in trips:
            for st, time in trip:
                if st == stop:
                    times.append(time)
        ret[stop] = list(map(lambda x: timediff(x[0], x[1]), zip(times[:-1], times[1:])))
    return ret

# get all the trips for the given route at the given date.
# returns a hash of (days) => [ trip ] where the list of trips
# has them classified by direction using the direction_id
def route_trips(db, route, date):
    weekdays = routetools.get_service_days(db, route)
    result = {}
    c = db.cursor()
    c1 = db.cursor()
    for wd in weekdays:
        d = [[],[]]
        for direction in (0, 1):
            c.execute("""SELECT trip_id FROM trips JOIN calendar USING(service_id)
                         WHERE route_id = ? AND direction_id = ?
                         AND start_date <= ? AND ? <= end_date
                         AND monday = ? AND tuesday = ? AND wednesday = ? AND thursday = ?
                         AND friday = ? AND saturday = ? AND sunday = ?""",
                         (route, direction, date, date) + wd)
            for trip_id in c:
                c1.execute("""SELECT stop_id, departure_time FROM stop_times
                              WHERE trip_id = ? AND departure_time != ''
                              ORDER BY stop_sequence""", trip_id)
                d[direction].append(Trip(trip_id[0], c1.fetchall()))
        result[wd] = d if len(d[0]) or len(d[1]) else []
    c.close()
    c1.close()
    return result
