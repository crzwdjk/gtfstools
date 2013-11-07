# routetools - a set of utilities for dealing with routes

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

# returns a list of tuples with one tuple for each set of days with a distinct service pattern
# for the given route.
def get_service_days(db, route):
    c = db.cursor()
    weekdays = []

    c.execute("""SELECT DISTINCT monday, tuesday, wednesday, thursday, friday, saturday, sunday
                 FROM trips JOIN calendar USING (service_id) WHERE route_id = ? """, (route,))
    # TODO: check that weekdays are non-overlapping
    for row in c:
        weekdays.append(tuple(row))

    return weekdays
