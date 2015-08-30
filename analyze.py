# analyze.py - utilities for analyzing GTFS data into a more tractable form
# currently contains only one function, to add a "segments" table.
# This table is a denormalization of a query that returns the stop-to-stop
# segments, grouped by route.

segments_sql = """
CREATE TABLE segments AS
SELECT
    st1.stop_id s1, st2.stop_id s2,
    trips.route_id route_id, count(*) ntrips,
    trips.direction_id direction_id
FROM
    stop_times st1, stop_times st2, trips
WHERE
    st1.trip_id = st2.trip_id
    AND st1.trip_id = trips.trip_id
    AND st1.stop_sequence < st2.stop_sequence
    AND NOT EXISTS (
        SELECT 1 FROM stop_times st3
        WHERE
            st3.trip_id = st1.trip_id
            AND st1.stop_sequence < st3.stop_sequence
            AND st3.stop_sequence < st2.stop_sequence
    )
GROUP BY
    s1, s2, route_id, direction_id
"""

def analyze(db):
    db.executescript(segments_sql)
