import time, calendar, urllib, requests, json
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import vincenty
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Basic location and radius (in miles)
location = 'State College, PA'
radius = 250

# Proximity for concert locations (in miles)
eps = 0.5

# Output columns
outputColumns = ['Bands', 'Date', 'Day', 'Location', 'Venue']

# Files
BANDS_FILE = 'bands.txt'
CONCERTS_FILENAME = 'concerts'
TEMPLATE_FILE = 'html/template.html'
STYLE_FILE = 'html/typography.css'


def getOriginCoords():
    origin = Nominatim().geocode(location)
    return {'lat': origin.latitude,
            'lon': origin.longitude}
# Origin coords
origin = getOriginCoords()


def queryByBand(name):
    url = 'http://api.bandsintown.com/artists/' + urllib.quote(name) + '/events.json'
    response = requests.get(url, params={'app_id': 'ConcertsAround'})
    return response.json()


def processData(data):
    result = []
    for concert in data:
        datetime = concert['datetime']
        processed = {'Bands': ', '.join([band['name'] for band in concert['artists']]),
                     'Date': datetime[:datetime.index('T')],
                     'Country': concert['venue']['country'],
                     'Region': concert['venue']['region'],
                     'City': concert['venue']['city'],
                     'Venue': concert['venue']['name'],
                     'lat': concert['venue']['latitude'],
                     'lon': concert['venue']['longitude']}
        if dist(origin, processed) < radius:
            result.append(processed)
    return result


def dist(first, second):
    return vincenty((first['lat'], first['lon']), (second['lat'], second['lon'])).miles


def mergeSortedData(data):
    index = 0
    while index < len(data)-1:
        if data[index]['Date'] == data[index+1]['Date'] and dist(data[index], data[index+1]) < eps:
            data[index]['Bands'] += ', ' + data[index+1]['Bands']
            del data[index+1]
        else:
            index += 1
    return data


def jsonToStr(jsonObj):
    return json.dumps(jsonObj, indent=4, sort_keys=True)


def dfToPDF(df):
    df['Location'] = df.City + ', ' + df.Region # + ' (' + df.Country + ')'
    df['Day'] = [calendar.day_name[date.weekday()] for date in df.Date]

    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(TEMPLATE_FILE)
    templateVars = {'title': 'Concerts',
                    'header': 'Concerts around {0} ({1} miles)'.format(location, radius),
                    'date': time.strftime("%Y-%m-%d"),
                    'table': df.to_html(columns=outputColumns, index=False)}
    htmlOutput = template.render(templateVars)
    HTML(string=htmlOutput).write_pdf('{}.pdf'.format(CONCERTS_FILENAME),
        stylesheets=[STYLE_FILE])


def main():
    data = []
    with open(BANDS_FILE, 'rb') as f:
        for band in f:
            data.extend(processData(queryByBand( band.strip() )))

    sortedData = sorted(data, key = lambda x: x['Date'] + x['Bands'])
    mergedData = mergeSortedData(sortedData)
    df = pd.read_json(jsonToStr(mergedData))
    dfToPDF(df)


if __name__ == '__main__':
    main()