# triptools - a set of tools for dealing with "trip" structures.


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

# check whether two routes "match", i.e. are going in the same direction
# through something like the same set of stops. a run of 3 matching stops
# is considered good enoguh.
def route_match(trip1, trip2):
    pos2 = 0
    count = 0
    for pos1 in range(len(trip1)):
        needle = trip1[pos1][0]
        for i in range(pos2, len(trip2)):
            if trip2[i][0] == needle:
                pos2 = i + 1
                count += 1
                break
        if pos2 >= len(trip2):
            break
    return count >= min(3, len(trip1), len(trip2))

# return a tuple of lists of trips that share segments
def classify(classes, trip):
    for i in range(len(classes)):
        if route_match(trip, classes[i][0]):
            if len(trip) > len(classes[i][0]):
                classes[i].append(classes[i][0])
                classes[i][0] = trip
            else:
                classes[i].append(trip)
            return
    classes.append([trip])

# try harder to coalesce the classified routes into a smaller
# number of classes
def classify_harder(classes):
    # find the smallest class
    # try to match that first one to each trip in each class.
    # Pick the best match.
    found_match = True
    while found_match:
        classes.sort(key=len)
        shortest = classes[0]
        found_match = False
        for target_cl in classes:
            if target_cl == shortest:
                continue
            for target in target_cl:
                if route_match(target, shortest[0]):
                    target_cl += shortest
                    del classes[0]
                    found_match = True
                    break
            if found_match:
                break
    return classes


# get all the trips for the given route at the given date.
# returns a hash of (days) => [ trip ] where the list of trips
# has them classified by direction.
def route_trips(db, route, date):
    weekdays = []
    result = {}
    c = db.cursor()
    c1 = db.cursor()
    c.execute("""SELECT DISTINCT monday, tuesday, wednesday, thursday, friday, saturday, sunday
                 FROM trips JOIN calendar USING (service_id) WHERE route_id = ? """, (route,))
    # TODO: check that weekdays are non-overlapping
    for row in c:
        weekdays.append(tuple(row))
    for wd in weekdays:
        classes = []
        result[wd] = []
        c.execute("""SELECT DISTINCT trip_id FROM trips JOIN calendar USING (service_id)
                     WHERE route_id = ? AND start_date <= ? AND ? <= end_date
                     AND monday = ? AND tuesday = ? AND wednesday = ? AND thursday = ?
                     AND friday = ? AND saturday = ? AND sunday = ?""",
                     (route, date, date) + wd)
        for row in c:
            c1.execute("""SELECT stop_id, departure_time FROM stop_times
                          WHERE trip_id = ? AND departure_time != ''
                          ORDER BY stop_sequence""", row)
            trip = c1.fetchall()
            classify(classes, trip)
        print([len(cl) for cl in classes])
        if len(classes) > 2:
           classes = classify_harder(classes)
        print([len(cl) for cl in classes])
        result[wd] = classes
    # return route lists for each day with a distinct set of trips.
    # dict of ((bool) * 7, list of (stop_id, time))
    c.close()
    c1.close()
    return result
