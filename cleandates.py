import csv, datetime, os, sys


def parsedate(d):
    y = int(d[0:4])
    m = int(d[4:6])
    d = int(d[6:8])
    return datetime.date(y, m, d)

def countdaysofweek(l):
    return set([ i.weekday() for i in l ])

dow = ['monday', 'tuesday', 'wednesday', 'thursday',
       'friday', 'saturday', 'sunday']

def dowsetfromrow(row):
    return set([ day for day, name in enumerate(dow) if row[name] == '1'])

def dowrowfromset(s):
    return { name: '1' if day in s else 0 for day, name in enumerate(dow) }

def main():
    if len(sys.argv) > 1:
        os.chdir(sys.argv[1])
    cr = csv.DictReader(open('calendar.txt', newline=''))
    calendar = list(cr)
    er = csv.DictReader(open('calendar_dates.txt', newline=''))
    exceptions = list(er)
    # find min, max service date and exception date
    max_date = '0'
    min_date = '99999999'
    servicedates = {}
    for c in calendar:
        d = parsedate(c['start_date'])
        e = parsedate(c['end_date'])
        servicedates[c['service_id']] = []
        dow = dowsetfromrow(c)
        while d <= e:
            if d.weekday() in dow:
                servicedates[c['service_id']].append(d)
            d = d + datetime.timedelta(1)
    for e in exceptions:
        if e['exception_type'] == '2':
            d = parsedate(e['date'])
            servicedates[e['service_id']].remove(d)
    for c in calendar:
        actualdow = countdaysofweek(servicedates[c['service_id']])
        allegeddow = dowsetfromrow(c)
        c.update(dowrowfromset(actualdow))
        diff = allegeddow - actualdow
        if diff:
            print("Removing dates " + repr(diff) + " from service " + c['service_id'])
        toremove = []
        for e in exceptions:
            if e['service_id'] == c['service_id']:
                if parsedate(e['date']).weekday() in diff:
                    toremove.append(e)
        for r in toremove:
            exceptions.remove(r)
                    
    cw = csv.DictWriter(open('newcalendar.txt', 'w'), cr.fieldnames)
    cdw = csv.DictWriter(open('newcalendar_dates.txt', 'w'), er.fieldnames)

    cw.writeheader()
    cw.writerows(calendar)

    cdw.writeheader()
    cdw.writerows(exceptions)

if __name__ == "__main__":
    main()    
                        
