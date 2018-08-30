import os, glob, argparse, time, calendar, requests, json, urllib.parse
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.distance import vincenty
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

class ConcertsFinder:
    # Proximity for concert locations to merge (in miles)
    eps = 0.5

    # Output columns
    outputColumns = ['Bands', 'Date', 'Day', 'Location', 'Venue']

    # URLs
    BASE_URL = 'https://rest.bandsintown.com/artists/'
    EVENTS = '/events'
    API_VERSION = '3.0.0'
    APP_ID = 'concerts_finder'

    STD_PARAMS = {'app_id': APP_ID}

    # Files
    BANDS_FILES = 'data/*.txt'
    TEST_BAND = 'test/test.txt'
    TEMPLATE_FILE = 'templates/template.html'
    STYLE_FILE = 'templates/typography.css'

    # Initialization with location and radius around it
    def __init__(self, location, radius):
        self.location = location
        self.radius = radius
        self.geolocator = Nominatim(user_agent='concert-finder')

    def get_coords(self, location):
        coords = self.geolocator.geocode(location)
        if coords != None:
            coords = {'lat': coords.latitude,
                      'lon': coords.longitude}
        return coords

    def dist(self, first, second):
        return vincenty((first['lat'], first['lon']), (second['lat'], second['lon'])).miles

    def query_by_band(self, name):
        url =  self.BASE_URL + urllib.parse.quote(name) + self.EVENTS
        response = requests.get(url, params=self.STD_PARAMS)
        return response.json()

    def process_data(self, data):
        result = []
        for concert in data:
            dt = concert['datetime']
            processed = {'Bands': ', '.join(concert['lineup']),
                         'Date': dt[:dt.index('T')],
                         'Country': concert['venue']['country'],
                         'Region': concert['venue']['region'],
                         'City': concert['venue']['city'],
                         'Venue': concert['venue']['name']}

            if  processed['Country'] == 'United States' or processed['Country'] == 'Canada':
                processed['Location'] = processed['City'] + ', ' + processed['Region']
            else:
                processed['Location'] = processed['City'] + ', ' + processed['Country']

            processed['Day'] = calendar.day_name[datetime.strptime(processed['Date'], '%Y-%m-%d').weekday()]

            if 'latitude' in concert['venue']:
                processed['lat'] = concert['venue']['latitude']
                processed['lon'] = concert['venue']['longitude']
            else:
                coords = self.get_coords(processed['Location'])
                if coords != None:
                    processed['lat'] = coords['lat']
                    processed['lon'] = coords['lon']

            if 'lat' in processed and self.dist(self.origin, processed) < self.radius:
                result.append(processed)
        return result

    def merge_sorted_data(self, data):
        index = 0
        while index < len(data)-1:
            if data[index]['Date'] == data[index+1]['Date'] and self.dist(data[index], data[index+1]) < self.eps:
                data[index]['Bands'] += ', ' + data[index+1]['Bands']
                del data[index+1]
            else:
                index += 1
        return data

    def json_to_str(self, jsonObj):
        return json.dumps(jsonObj, indent=4, sort_keys=True)

    def df_to_pdf(self, df, fileName):
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template(self.TEMPLATE_FILE)
        templateVars = {'title': 'Concerts',
                        'header': 'Concerts around {0} ({1} miles)'.format(self.location, self.radius),
                        'date': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'table': df.to_html(columns=self.outputColumns, index=False)}
        htmlOutput = template.render(templateVars)
        HTML(string=htmlOutput).write_pdf('{}.pdf'.format(fileName), stylesheets=[self.STYLE_FILE])

    def find(self):
        self.origin = self.get_coords(self.location)

        curDir = os.getcwd()
        os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

        for fileName in glob.glob(self.BANDS_FILES):
            data = []
            with open(fileName, 'rb') as f:
                for band in f:
                    data.extend(self.process_data(self.query_by_band( band.strip() )))

            sortedData = sorted(data, key = lambda x: x['Date'] + x['City'] + x['Bands'])
            mergedData = self.merge_sorted_data(sortedData)
            if mergedData:
                df = pd.read_json(self.json_to_str(mergedData))
                self.df_to_pdf(df, os.path.splitext(os.path.basename(fileName))[0])

        os.chdir(curDir)

    def test(self):
        self.origin = self.get_coords(self.location)

        curDir = os.getcwd()
        os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

        data = []
        with open(self.TEST_BAND, 'rb') as f:
            for band in f:
                data.extend(self.process_data(self.query_by_band( band.strip() )))

        sortedData = sorted(data, key = lambda x: x['Date'] + x['City'] + x['Bands'])
        mergedData = self.merge_sorted_data(sortedData)
        if mergedData:
            df = pd.read_json(self.json_to_str(mergedData))
            self.df_to_pdf(df, os.path.splitext(os.path.basename(self.TEST_BAND))[0])

        os.chdir(curDir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='''Find concerts of favorite bands around you.
        The algorithm processes all text files in 'data' folder.
        Each line in a text file should consist of a single band name.''')
    parser.add_argument('-l', nargs='?', type=str, default='New York, NY',
        metavar='location', help='location to search')
    parser.add_argument('-d', nargs='?', type=int, default=500,
        metavar='distance', help='radius of neighborhood (in miles)')
    args = parser.parse_args()

    finder = ConcertsFinder(args.l, args.d)
    finder.find()
