module GTFSUtils
  def get_route_stops(db, route)
    db.results_as_hash = false
    stop_hash = db.execute(%q{
        select stops.stop_id, stops.stop_name
        from stop_times, trips, stops
        where stop_times.trip_id = trips.trip_id and trips.route_id = ? and stop_times.stop_id = stops.stop_id}, route).to_h
    d0_segs = db.execute('select distinct s1, s2 from segments where route_id = ? and direction_id = 0', route)
    d1_segs = db.execute('select distinct s1, s2 from segments where route_id = ? and direction_id = 1', route)
    order_stops(d0_segs) + order_stops(d1_segs)
    s1 = order_stops(d0_segs).map { |x| x.map { |y| [y, stop_hash[y]] }}
    s2 = order_stops(d1_segs).map { |x| x.map { |y| [y, stop_hash[y]] }}
    s1 + s2
  end

  # order_stops :: [ (stop_id, stop_id) ] -> [ [ stop_id ] ]
  def order_stops(segments)
    pile = segments.map { |x| [x[0], x[1]] }
    return [] if pile.length == 0
    result = [ pile.pop ]
    while pile.length > 0
      forward_segs = pile.select { |i| i[0] == result[-1][-1] }
      found = false
      if forward_segs.length == 1
        result[-1] += forward_segs[0][1..-1]
        pile.delete(forward_segs[0])
        found = true
      end
      backward_segs = pile.select { |i| i[1] == result[-1][0] }
      if backward_segs.length == 1
        result[-1].unshift(*backward_segs[0][0..-2])
        pile.delete(backward_segs[0])
        found = true
      end
      if pile.length > 0 and not found
        result << pile.pop
      end
    end
    return result
    # so now result is a list of branches. Flatten segments.
    while true
      result[0...-1].each_index do |i|
        appended = false
        appends = result[(i + 1) .. -1].select do |s|
          s[0] == result[i][-1]
        end.sort { |a, b| a.length <=> b.length }
        prepends = result[(i + 1) .. -1].select do
          |s| s[-1] == results[i][0]
        end.sort { |a, b| a.length <=> b.length }
        if appends.length > 0
          results[i] << appends[0]
          appended = true
        end
        if prepends.length > 0 
          results[i].unshift(prepends[0]) if prepends.length > 0
          appended = true
        end
        break unless appended
      end
    end
    
    return result 
  end



end
