import json
import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
import pickle
from bs4 import BeautifulSoup
import logging
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
from email.utils import parsedate_tz, mktime_tz

class Message:
    def __init__(self, date, sender, subject, body):
        self.date = date
        self.sender = sender
        self.subject = subject
        self.body = body

    def __str__(self):
        return f"{self.date}\n{self.sender}\n{self.subject}\n{self.body}"

class Forecast_Request:
    def __init__(self, location=None, elevation=None, model=None, start=None, 
                 test=None):
        if location is None:
            location = '62.950,-151.091'
        self.location = location
        if elevation is None:
            elevation = ''
        self.elevation = elevation
        if model is None:
            model = 'mbd'
        self.model = model
        if start is None:
            start = ''
        self.start = start
        if test is None:
            test = False
        self.test = test

    def __str__(self):
        return f"{self.location}\n{self.elevation}\n{self.model}\n{self.start} \
            \ntest: {self.test}"


def configure():
    # loads secret variables
    load_dotenv()


def retrieve_emails(secret_file, max_retrievals):
    #variable creds stores the user access token
    creds = None
    if os.path.exists('token.pickle'):
        #reads the token from the file and store it in the variable creds
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        logger.debug('token file exists')
    # if credentials are not available or are invalid, ask the user to log in
    if not creds or not creds.valid:
        logger.debug('token no longer valid')
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, ['https://www.googleapis.com/auth/gmail.readonly'])
            creds = flow.run_local_server(port=0)
        # saves the access token in token.pickle file for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # connects to the Gmail API and gets messages
    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().list(maxResults=max_retrievals, userId='me', includeSpamTrash='booleanTrue').execute()
    messages = result.get('messages')
    # messages is a list of dictionaries where each dictionary contains a message id
    logger.info('retrieved ' + str(len(messages)) + ' emails')
    
    # gets plaintext from message dictionaries
    plaintext_messages = []
    for msg in messages:
        # gets the message from its id
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        try:
            # get value of 'payload' from dictionary 'txt'
            payload = txt['payload']
            headers = payload['headers']
            # looks for Subject and Sender Email in the headers
            for d in headers:
                if d['name'] == 'Subject':
                    subject = d['value']
                if d['name'] == 'From':
                    sender = d['value']
                if d['name'] == 'Date':
                    date = d['value']
            # get the data of the body and decodes it with base 64 decoder
            if 'parts' in payload.keys():
                parts = payload.get('parts')[0]
                data = parts['body']['data']
            else:
                data = payload.get('body')['data']
            data = data.replace("-", "+").replace("_", "/")
            decoded_data = base64.b64decode(data)
            # parses lxml datap
            soup = BeautifulSoup(decoded_data, "lxml")
            body = soup.body()
            plaintext_messages.append(Message(date, sender, subject, body))
        except Exception as e:
            logger.warning(e)
            pass
    
    logger.debug('decoded ' + str(len(plaintext_messages)) + ' emails')
    return plaintext_messages


def filter_new_forecast_requests(emails_requests, ignore_previous_to):
    new_requests = []
    for msg in emails_requests:
        if mktime_tz(parsedate_tz(msg.date)) > mktime_tz(parsedate_tz(ignore_previous_to)):
            if '$get forecast$' in BeautifulSoup(str(msg.body), 'html.parser').get_text():
                new_requests.append(msg)
    logger.info('found ' + str(len(new_requests)) + ' new forecast request(s)')
    return new_requests


# reads email and extracts the forecast request
def extract_request_from_message(msg):
    req = Forecast_Request()
    if '$model ' in str(msg.body):
        req.model = str(msg.body).split('$model ')[1].split('$')[0]
    if '$loc ' in str(msg.body):
        req.location = str(msg.body).split('$loc ')[1].split('$')[0]
    if '$elev ' in str(msg.body):
        req.elevation = str(round(int(str(msg.body).split('$elev ')[1].split('$')[0])/3.28084))
    if '$start ' in str(msg.body):
        req.start = str(msg.body).split('$start ')[1].split('$')[0]
    if '~test~' in str(msg.body):
        req.test = True
    else:
        req.test = False
    return req


# retrieves forecast from MeteoBlue API
def get_meteoblue_forecast(location, elev, model):
    # builds url for requested model
    if model == 'mb6':
        url = "https://my.meteoblue.com/packages/basic-1h_clouds-1h?apikey=" + \
              os.getenv('METEOBLUE_API_KEY') + "&" + location_lookup(location) + "&"
        if elev != "" and 0 < int(elev) < 8848:
            url += 'asl=' + elev + "&"
        url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"
    elif model == 'mb3':
        url = "https://my.meteoblue.com/packages/basic-1h_clouds-1h?apikey=" + \
              os.getenv('METEOBLUE_API_KEY') + "&" + location_lookup(location) + "&"
        if elev != "" and 0 < int(elev) < 8848:
            url += 'asl=' + elev + "&"
        url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"
    else:
        # if bad model request give 7 day forecast as default
        if model != 'mbd':
            logger.warning('bad model request, giving 7 day forecast as default')
        url = "https://my.meteoblue.com/packages/trendpro-day?apikey=" + \
              os.getenv('METEOBLUE_API_KEY') + "&" + location_lookup(location) + "&"
        if elev != "" and 0 < int(elev) < 8848:
            url += 'asl=' + elev + "&"
        url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"
    
    # checks if a recent (<3hr ago) model is already saved
    forecast_filename = model + "_" + location + '_' + elev + '.json'
    if os.path.exists(FORECASTS_FOLDER+forecast_filename):
        with open(FORECASTS_FOLDER+forecast_filename, 'r') as file:
            saved_forecast = json.load(file)
        if datetime.strptime(saved_forecast['metadata']['modelrun_utc'], 
                             '%Y-%m-%d %H:%M') + timedelta(hours=3) > datetime.utcnow():
            logger.info('requested forecast already retrived recently at ' + 
                        saved_forecast['metadata']['modelrun_utc'])
            return
    # gets a new model from meteoblue
    logger.info('getting forecast from ' + 
        url.split(os.getenv('METEOBLUE_API_KEY'))[0] + 
        "****************" + url.split(os.getenv('METEOBLUE_API_KEY'))[1])
    response = requests.get(url).json()
    with open(FORECASTS_FOLDER+forecast_filename, "w") as file:
        json.dump(response, file)


# takes requested location and returns correctly formatted location if possible
def location_lookup(loc):
    if ', ' in loc:
        return 'lat=' + loc.split(', ')[0] + '&lon=' + loc.split(', ')[1]
    elif ',' in loc:
        return 'lat=' + loc.split(',')[0] + '&lon=' + loc.split(',')[1]
    else:
        logger.warning('bad location, giving Begguya forecast as default')
        return "mount-hunter_united-states_5864415"


# combines headers and forecast data to return string of forecast in sms length
def build_sms_forecast(location, elev, model, request_start):
    with open(FORECASTS_FOLDER + model + "_" + location + '_' + elev + '.json', 'r') as file:
            forecast = json.load(file)
    if model == 'mb6':
        # if no request start specifified, make start of available forecast
        if request_start == '':
            request_start = forecast['metadata']['modelrun_utc'][-8:-3]
        model_tag = '6'
        formatted_data = format_6hr_forecast(forecast['data_1h'], request_start)
    elif model == 'mb3':
         # if no request start specifified, make start of available forecast
        if request_start == '':
            request_start = forecast['metadata']['modelrun_utc'][-8:-3]
        model_tag = '3'
        formatted_data = format_3hr_forecast(forecast['data_1h'], request_start)
    # if model == 'mbd' give daily forecast, or if bad model is requested give daily by default
    else:
        # if no request start specifified, make start of available forecast
        if request_start == '':
            request_start = forecast['metadata']['modelrun_utc'][-8:-6]
        model_tag = 'D'
        formatted_data = format_day_forecast(forecast['trend_day'], request_start)
    return compress_loc(forecast) + ' ' + str(round(int(forecast['metadata']['height'])*.00328084)) + ' ' + model_tag + '\n' + ''.join(formatted_data)


# returns string of location without unnecesary characters to send to inreach
def compress_loc(forecast):
    lat = forecast['metadata']['latitude']
    lon = forecast['metadata']['longitude']
    return (str(lat).split('.')[0] + str(lat).split('.')[1][:1]).ljust(4) + (str(lon).split('.')[0] + str(lon).split('.')[1][0:1]).rjust(5)


# formats 7 day (24-hour incriment) Meteoblue data for sms inreach reply
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


# formats 1 day (3-hour incriment) Meteoblue data for sms inreach reply
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


# formats 2 day (6-hour incriment) Meteoblue data for sms inreach reply
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
        wind_dir += mb_1hr['winddirection'][hr1+3].rjust(2)
        if int(mb_1hr['time'][hr1][-5:-3]) > 17:
            temp, snow, precip_prob, clear, wind, wind_dir = (x + '*' for x in (temp, snow, precip_prob, clear, wind, wind_dir))

    time, temp, snow, precip_prob, clear, wind= (x + '\n' for x in (time, temp, snow, precip_prob, clear, wind))

    return [time, temp, snow, precip_prob, clear, wind, wind_dir]


# finds reply URL in email
def extract_map_share_url(text):
    url = re.search("(?P<url>https?://[^\s]+)", text).group("url")
    if url == 'http://explore.garmin.com/inreach':
        url = os.getenv('FALLBACK_INREACH_REPLY_URL')
    return url


# combines mapshare URL and sms forecast into HTML payload
def create_map_share_payload(url, text):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    message_id = soup.find("input", {"id": "MessageId"}).get('value')
    guid = soup.find("input", {"id": "Guid"}).get('value')
    reply_address = soup.find("input", {"id": "ReplyAddress"}).get('value')
    return {'ReplyAddress': reply_address,
            'ReplyMessage': text,
            'MessageId': message_id,
            'Guid': guid}


# opens MapShare and sends message
def notify_map_share(url, text, test):
    payload = create_map_share_payload(url, text)
    logger.debug(payload)
    session = requests.Session()
    if not test:
        response = session.post(
            'https://us0.explore.garmin.com/textmessage/txtmsg',
            headers={'User-Agent': 'Mozilla/5.0'},
            data=payload)
        logger.info('sending via ' + url.split('?extId=')[0] + 
                    '?extId=************' + url.split('?extId=')[1][12:])
        logger.debug(response)
        return response.ok
    else:
        logger.info('this forecast request is a test')
        return test


def update_prev_read_log(msg, log):
    with open(log, 'r') as file:
        last_read = file.read()
    if mktime_tz(parsedate_tz(msg.date)) > mktime_tz(parsedate_tz(last_read)):
        with open(log, 'w') as file:
            file.write(msg.date)


def main():
    configure()
    # retrieves messages from gmail
    msgs = retrieve_emails(os.getenv('GOOGLE_SECRET_FILE'), 50)
    # makes list of messages that are forecast requests and new
    with open(EMAIL_READ_LOG, "r") as file:
            ignore_previous_to = file.read()
    new_request_messages = filter_new_forecast_requests(msgs, ignore_previous_to)
    # sends forecast for each request message
    for message in new_request_messages:
        inreach_req = extract_request_from_message(message)
        logger.info('inreach forecast request:\n' + str(inreach_req))
        get_meteoblue_forecast(inreach_req.location, inreach_req.elevation, inreach_req.model)
        reply = build_sms_forecast(inreach_req.location, inreach_req.elevation, inreach_req.model, inreach_req.start)
        logger.info('weather forecast reply:\n' + reply)
        map_share_url = extract_map_share_url(str(message))
        first_try_success = notify_map_share(map_share_url, reply, inreach_req.test)
        if not first_try_success:
            logger.warning('reply url failed! retrying via fallback url')
            notify_map_share(os.getenv('FALLBACK_INREACH_REPLY_URL'), reply, inreach_req.test)
        update_prev_read_log(message, EMAIL_READ_LOG)


FORECASTS_FOLDER = 'forecasts/'
MB_LOCATIONS_LIST = 'forecast_locations.json'
EMAIL_READ_LOG = 'previously_read_log.txt'

logging.basicConfig(filename="logs/" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

main()