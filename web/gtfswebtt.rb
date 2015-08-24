Camping.goes :Timetable

module Timetable::Controllers
  class Index
    def get
      @agencies = list_agencies()
      render :agency_list
    end
  end

  class Agency < R '/([^/]+)'
    def get(agency)
      @routes = get_routes(agency)
      @agid = agency
      (@agency, @city) = agency.split('_')
      render :agency_routes
    end
  end

  class Route < R '/([^/]+)/route/([^/]+)'
    def get(agency, routeid)
      @agid = agency
      db = agencydbh(agency)
      (@agency, @city) = agency.split('_')
      @routeinfo = route_info(routeid)
      @stops = get_route_stops(db,routeid)
      render :route_stops
    end
  end
  class Stop < R '/([^/]+)/stop/(\d+)'
    def get(agency, stop)
      @agid = agency
      @stop_routes = stop_routes(stop)
      @stop_info = stop_info(stop)
      # split version
      @service_ids = pick_services(Date.today)
      @stop_trips = @stop_routes.map { |rt| [ rt['route_id'], stop_trips(services, rt['route_id'])] }.to_h
      render :stop_timetable
    end
  end
end

module Timetable::Views
  def agency_list
    h3 "Pick your transit agency:"
    table do
      thead { th "Agency" ; th "City" }
      @agencies.each do |ag|
        (city, agency) = ag.split("_")
        tr do
          td { a agency, :href => R(Agency, ag) }
          td city
        end
      end
    end
  end
  def agency_routes
    h1 "#{@agency} (#{@city})"
    ul do
      for route in @routes
        li do
          name = route_name(route)
          a name, :href => R(Route, @agid, route['route_id'])
        end
      end
    end
  end
  def route_stops
    routename = route_name(@routeinfo)
    h1 "#{routename} #{@agency} (#{@city})"
    for direction in @stops
      ul do
        for stop in direction
          li { a "#{stop[1]}", :href => R(Stop, @agid, stop[0]) }
        end
      end
    end
  end
  def stop_timetable
    routenames = @stop_routes.map { |r| route_name(r) }.join ','
    h1 "#{stop_info['stop_name']} (#{routenames}) "
    # route header
    # day of week header.., ugh and what if Monday-Thursday
    # and Friday services are actually the same?
    timetable.each_key do |routeid|
      h3 route_name(stop_routes[routeid])
      table do
        thead do
          timetable['route_id'].each do |service, trips|
            th service['days']
          end
        end
        tr do 
          timetable['route_id'].each do |service, trips|
            td do 
              hour = nil
              table 
              rows = []
              trips.each do |time, note|
                if time[0] != hour
                  rows << []
                  rows[-1][0] = hour
                end
                rows[-1] << time[1] + note
              end
              rows.each do |row|
                tr do
                  td row[0]
                  row[1..-1].join(" ")
                end
              end
            end
          end
        end
        tr do 
          td :colspan => '99' do 
            timetable['notes'].each do |letter, text|
              div do
                span letter
                span text
              end
            end
          end
        end
      end
    end
  end
end

require 'sqlite3'
require_relative 'gtfsutils'
module Timetable::Helpers
  include GTFSUtils
  def gtfsdir; ENV['HOME'] + "/gtfs/"; end
  def agencydbh(agency)
    if not $dbhcache[agency]
      db = SQLite3::Database.new(gtfsdir + agency + '.db')
      db.enable_load_extension(true)
      db.load_extension('libspatialite')
      db.enable_load_extension(false)
      db.collation('routesort', collation(lambda {|x,y| routesort(x, y)}))
      $dbhcache[agency] = db
    else
      $dbhcache[agency]
    end
  end
  def list_agencies()
    Dir.new(gtfsdir).select {|f| f.match(/^(.*\.db)/) }.map do
      |x| x.match(/^(.*)\.db/)[1]
    end
  end
  def get_routes(agency)
    db = agencydbh(agency)
    db.results_as_hash = true
    rows = db.execute('select route_id, route_short_name, route_long_name, route_type, agency_id from routes order by route_short_name collate routesort')
  end
  def route_info(routeid)
    db = agencydbh(@agid)
    db.results_as_hash = true
    rows = db.execute('select route_id, route_short_name, route_long_name, route_type, agency_id from routes where route_id = ?', routeid)[0]
  end
  def route_name(route)
    if route['route_long_name'] != ''
      route['route_long_name']
    elsif route['route_short_name'] != ''
      route['route_short_name']
    else
      route['route_id']
    end
  end
  
  def collation(block)
    Class.new do
      @blk = block
      instance_eval do
        def compare(x, y); @blk.call(x,y); end
      end
    end
  end

  def routesort(x, y)
    re = /^(\D*)(\d*)(.*)$/
    a = x.match(re).to_a[1..-1]
    a[1] = a[1].to_i
    b = y.match(re).to_a[1..-1]
    b[1] = b[1].to_i
    a.zip(b).map { |c, d| c <=> d }.inject { |p, n| p == 0 ? n : p }
  end  

  def hashgroup(arr, key)
    h = {}
    arr.each do |row|
      h[row[key]] ||= []
      h[row[key]].append(row)
    end
  end
end

def Timetable.create
  $dbhcache = {}
end
