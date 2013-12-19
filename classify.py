
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
            return i
    classes.append([trip])
    return len(classes) - 1

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
# has them classified by direction using our homegrown
# classification algorithm
def route_trips(db, route, date):
    weekdays = routetools.get_service_days(db, route)
    result = {}
    c = db.cursor()
    c1 = db.cursor()
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
            trip = Trip(row[0], c1.fetchall())
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
