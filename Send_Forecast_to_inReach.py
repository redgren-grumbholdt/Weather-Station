import json
import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
import pickle


class Message:
    def __init__(self, date, sender, subject, body):
        self.date = date
        self.sender = sender
        self.subject = subject
        self.body = body

    def __str__(self):
        return f"{self.date}\n{self.sender}\n{self.subject}\n{self.body}"


class Request:
    def __init__(self, location=None, elevation=None, model=None, start=None):
        if location is None:
            location = 'begguya'
        self.location = location
        if elevation is None:
            elevation = ''
        self.elevation = elevation
        if model is None:
            model = 'Md'
        self.model = model
        if start is None:
            start = ''
        self.start = start

    def __str__(self):
        return f"{self.location}\n{self.elevation}\n{self.model}\n{self.start}"


def configure():
    load_dotenv()


def loc_lookup(loc):
    with open(MB_LOCATIONS_LIST, 'r') as file:
        locations = json.load(file)
    if loc in locations:
        return locations[loc]
    elif ',' in loc:
        return 'lat=' + loc.split(',')[0] + '&lon=' + loc.split(',')[1]
    else:
        # can change this to return an error
        return "!bad location!"


def get_forecast(location, elev, model):
    # builds url for requested model
    if model == 'mbd':
        url = "https://my.meteoblue.com/packages/trendpro-day?apikey=" + os.getenv('METEOBLUE_API_KEY') + "&" + loc_lookup(location) + "&"
        if elev != "":
            url += 'asl=' + elev + "&"
        url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"
    elif model == 'mb6':
        url = "https://my.meteoblue.com/packages/basic-1h_clouds-1h?apikey=" + os.getenv('METEOBLUE_API_KEY') + "&" + loc_lookup(location) + "&"
        if elev != "":
            url += 'asl=' + elev + "&"
        url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"
    elif model == 'mb3':
        url = "https://my.meteoblue.com/packages/basic-1h_clouds-1h?apikey=" + os.getenv('METEOBLUE_API_KEY') + "&" + loc_lookup(location) + "&"
        if elev != "":
            url += 'asl=' + elev + "&"
        url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"
    else:
        # add error handling here
        return
    print(url)
    # checks if a recent (<3hr) model is already saved
    forecast_filename = model + "_" + location + '_' + elev + '.json'
    if os.path.exists(FORECASTS_FOLDER+forecast_filename):
        with open(FORECASTS_FOLDER+forecast_filename, 'r') as file:
            saved_forecast = json.load(file)
        if datetime.strptime(saved_forecast['metadata']['modelrun_utc'], '%Y-%m-%d %H:%M') + timedelta(hours=3) > datetime.utcnow():
            print('already gotten')
            return
    # gets a new model from meteoblue
    response = requests.get(url).json()
    with open(FORECASTS_FOLDER+forecast_filename, "w") as file:
        json.dump(response, file)


def compress_loc(location):
    for prefix in ('mount ', 'mt ', 'pt ', 'pt. ', 'point'):
        if prefix in location:
            return location.split(prefix)[0]
    if ',' in location:
        return location.split(',')[0][-2:] + location[-2:]
    else:
        return location


def text_forecast(location, elev, model, request_start):
    with open(FORECASTS_FOLDER + model + "_" + location + '_' + elev + '.json', 'r') as file:
            forecast = json.load(file)
    if model == 'mbd':
        # if no request start specifified, make start of available forecast
        if request_start == '':
            request_start = forecast['metadata']['modelrun_utc'][-8:-6]
        return compress_loc(location)[0:4] + str(round(int(forecast['metadata']['height'])*.00328084)).rjust(2, '0') + 'mD\n' + ''.join(format_day_forecast(forecast['trend_day'], request_start))
    elif model == 'mb6':
        # if no request start specifified, make start of available forecast
        if request_start == '':
            request_start = forecast['metadata']['modelrun_utc'][-8:-3]
        return compress_loc(location)[0:4] + str(round(int(forecast['metadata']['height'])*.00328084)).rjust(2, '0') + 'm6\n' + ''.join(format_6hr_forecast(forecast['data_1h'], request_start))
    elif model == 'mb3':
         # if no request start specifified, make start of available forecast
        if request_start == '':
            request_start = forecast['metadata']['modelrun_utc'][-8:-3]
        return compress_loc(location)[0:4] + str(round(int(forecast['metadata']['height'])*.00328084)).rjust(2, '0') + 'm3\n' + ''.join(format_3hr_forecast(forecast['data_1h'], request_start))
    else:
        # add error handling here
        return


def format_day_forecast(mb_day, req_start):
    start = None
    for offset, day in enumerate(mb_day['time']):
        if day[-8:-6] == req_start and len(mb_day['time']) >= offset + 7:
            start = offset
    if start == None:
        return ['Cannot retrieve the forecast for the days requested. Current available daily forecast is for ' + mb_day['time'][0][-8:-6] + '-' + mb_day['time'][-1][-8:-6]]
    
    time = ''
    high = 'H'
    low = 'L'
    snow = 'S'
    precip_prob = 'P'
    clear = 'C'
    wind = 'W'
    gust = 'G'
    wind_dir = 'D'
    predictability = '%'
    
    time += mb_day['time'][start][-8:-6] + '-' + mb_day['time'][start+6][-8:-6]

    for day in range(7):
        high += str(round(float(mb_day['temperature_max'][start+day]))).rjust(3)
        low += str(round(float(mb_day['temperature_min'][start+day]))).rjust(3)
        snow_eq = float(mb_day['precipitation'][start+day]) * 10 * float(mb_day['snowfraction'][start+day])
        if snow_eq < .05:
            snow += '  -'
        elif snow_eq > .95:
            snow += str(round(snow_eq)).rjust(3)
        else:
            snow += str(round(snow_eq, 1))[-2:].rjust(3)
        precip_prob += str(round(float(mb_day['precipitation_probability'][start+day])/10)).rjust(2)
        clear += str(round(float(mb_day['sunshinetime'][start+day])/60)).rjust(3)
        wind += str(round(float(mb_day['windspeed_max'][start+day])/10)).rjust(2)
        gust += str(round(float(mb_day['gust_mean'][start+day]))).rjust(3)
        wind_dir += mb_day['winddirection'][start+day].rjust(3)
        predictability += str(round(float(mb_day['predictability'][start+day])/10)).rjust(2)

    time, high, low, snow, precip_prob, clear, wind, gust, wind_dir = (x + '\n' for x in (time, high, low, snow, precip_prob, clear, wind, gust, wind_dir))

    return [time, high, low, clear, snow, precip_prob, wind, predictability]


def format_3hr_forecast(mb_1hr, req_start):
    start = None
    for offset, day in enumerate(mb_1hr['time']):
        if day[-8:-3] == req_start and len(mb_1hr['time']) >= offset + (8*3+2):
            start = offset
    if start == None:
        return ['Cannot retrieve the forecast for the days requested. Current available 3hr forecast is for ' + mb_1hr['time'][0][-8:-3] + '-' + mb_1hr['time'][-1][-8:-3]]
    
    time = ''
    temp = 'T'
    snow = 'S'
    precip_prob = 'P'
    clear = 'C'
    wind = 'W'
    wind_dir = 'D'
    
    time += mb_1hr['time'][start][-8:-6] + mb_1hr['time'][start][-5:-3] + '*' + mb_1hr['time'][start+(7*3)][-8:-6]

    for period in range(8):
        hr1 = start + period*3
        hr3 = start + period*3 + 2
        
        temp += str(round(sum([float(temp) for temp in mb_1hr['temperature'][hr1:hr3]])/len([float(temp) for temp in mb_1hr['temperature'][hr1:hr3]]))).rjust(3)
        snow_eq = sum([float(snow) for snow in mb_1hr['precipitation'][hr1:hr3]]) * 10
        if snow_eq < .05:
            snow += '  -'
        elif snow_eq > .95:
            snow += str(round(snow_eq)).rjust(3)
        else:
            snow += str(round(snow_eq, 1))[-2:].rjust(3)
        precip_prob += str(round(max([float(prob) for prob in mb_1hr['precipitation_probability'][hr1:hr3]])/10)).rjust(2)
        clear += str(round(sum([float(mins) for mins in mb_1hr['sunshinetime'][hr1:hr3]])/60)).rjust(2)
        wind += str(round(max([float(mph) for mph in mb_1hr['windspeed'][hr1:hr3]])/10)).rjust(2)
        wind_dir += mb_1hr['winddirection'][hr1+1].rjust(3)
        if int(mb_1hr['time'][hr1][-5:-3]) > 20:
            temp, snow, precip_prob, clear, wind, wind_dir = (x + '*' for x in (temp, snow, precip_prob, clear, wind, wind_dir))

    time, temp, snow, precip_prob, clear, wind= (x + '\n' for x in (time, temp, snow, precip_prob, clear, wind))

    return [time, temp, snow, precip_prob, clear, wind, wind_dir]


def format_6hr_forecast(mb_1hr, req_start):
    start = None
    for offset, day in enumerate(mb_1hr['time']):
        if day[-8:-3] == req_start and len(mb_1hr['time']) >= offset + (8*6+5):
            start = offset
    if start == None:
        return ['Cannot retrieve the forecast for the days requested. Current available 6hr forecast is for ' + mb_1hr['time'][0][-8:-3] + '-' + mb_1hr['time'][-1][-8:-3]]
    
    time = ''
    temp = 'T'
    snow = 'S'
    precip_prob = 'P'
    clear = 'C'
    wind = 'W'
    wind_dir = 'D'
    
    time += mb_1hr['time'][start][-8:-6] + mb_1hr['time'][start][-5:-3] + '*' + mb_1hr['time'][start+(7*6)][-8:-6]

    for period in range(8):
        hr1 = start + period*6
        hr6 = start + period*6 + 5
        
        temp += str(round(sum([float(temp) for temp in mb_1hr['temperature'][hr1:hr6]])/len([float(temp) for temp in mb_1hr['temperature'][hr1:hr6]]))).rjust(3)
        snow_eq = sum([float(snow) for snow in mb_1hr['precipitation'][hr1:hr6]]) * 10
        if snow_eq < .05:
            snow += '  -'
        elif snow_eq > .95:
            snow += str(round(snow_eq)).rjust(3)
        else:
            snow += str(round(snow_eq, 1))[-2:].rjust(3)
        precip_prob += str(round(max([float(prob) for prob in mb_1hr['precipitation_probability'][hr1:hr6]])/10)).rjust(2)
        clear += str(round(sum([float(mins) for mins in mb_1hr['sunshinetime'][hr1:hr6]])/60)).rjust(2)
        wind += str(round(max([float(mph) for mph in mb_1hr['windspeed'][hr1:hr6]])/10)).rjust(2)
        wind_dir += mb_1hr['winddirection'][hr1+3].rjust(3)
        if int(mb_1hr['time'][hr1][-5:-3]) > 17:
            temp, snow, precip_prob, clear, wind, wind_dir = (x + '*' for x in (temp, snow, precip_prob, clear, wind, wind_dir))

    time, temp, snow, precip_prob, clear, wind= (x + '\n' for x in (time, temp, snow, precip_prob, clear, wind))

    return [time, temp, snow, precip_prob, clear, wind, wind_dir]


def load_messages(email_pickle):
    with open(email_pickle, 'rb') as file:
        return pickle.load(file)


def request_from_message(msg):
    req = Request()
    if '$model ' in str(msg.body):
        req.model = str(msg.body).split('$model ')[1].split('$')[0]
    if '$loc ' in str(msg.body):
        req.location = str(msg.body).split('$loc ')[1].split('$')[0]
    if '$elev ' in str(msg.body):
        req.elevation = str(round(int(str(msg.body).split('$elev ')[1].split('$')[0])/3.28084))
    if '$start ' in str(msg.body):
        req.start = str(msg.body).split('$start ')[1].split('$')[0]
    return req


def main():
    configure()
    messages = load_messages(MESSAGES_FILE)
    for message in messages:
        request = request_from_message(message)
        print(request)
        get_forecast(request.location, request.elevation, request.model)
        reply = text_forecast(request.location, request.elevation, request.model, request.start)
        print(reply)
        print(len(reply))


FORECASTS_FOLDER = 'forecasts/'
MESSAGES_FILE = 'new_messages.pickle'
MB_LOCATIONS_LIST = 'forecast_locations.json'

main()