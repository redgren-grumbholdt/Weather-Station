from bs4 import BeautifulSoup
import requests
import time
from datetime import datetime
from selenium import webdriver
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
import base64
from email.utils import parsedate_tz, mktime_tz
import json


class Message:
    def __init__(self, date, sender, subject, body):
        self.date = date
        self.sender = sender
        self.subject = subject
        self.body = body

    def __str__(self):
        return f"{self.date}\n{self.sender}\n{self.subject}\n{self.body}"


def retrieve_emails(secret_file, retrievals):
    # Variable creds will store the user access token.
    # If no valid token found, we will create one.
    creds = None

    # The file token.pickle contains the user access token.
    # Check if it exists
    if os.path.exists('token.pickle'):
        # Read the token from the file and store it in the variable creds
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If credentials are not available or are invalid, ask the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the access token in token.pickle file for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Connect to the Gmail API
    service = build('gmail', 'v1', credentials=creds)

    # We can also pass maxResults to get any number of emails. Like this:
    result = service.users().messages().list(maxResults=retrievals, userId='me', includeSpamTrash='booleanTrue').execute()
    messages = result.get('messages')

    # messages is a list of dictionaries where each dictionary contains a message id.

    plaintext_messages = []

    # iterate through all the messages
    for msg in messages:
        # Get the message from its id
        txt = service.users().messages().get(userId='me', id=msg['id']).execute()

        # Use try-except to avoid any Errors
        try:
            # Get value of 'payload' from dictionary 'txt'
            payload = txt['payload']
            headers = payload['headers']

            # Look for Subject and Sender Email in the headers
            for d in headers:
                if d['name'] == 'Subject':
                    subject = d['value']
                if d['name'] == 'From':
                    sender = d['value']
                if d['name'] == 'Date':
                    date = d['value']

            # The Body of the message is in Encrypted format. So, we have to decode it.
            # Get the data and decode it with base 64 decoder.
            if 'parts' in payload.keys():
                parts = payload.get('parts')[0]
                data = parts['body']['data']
            else:
                data = payload.get('body')['data']
            data = data.replace("-", "+").replace("_", "/")
            decoded_data = base64.b64decode(data)

            # Now, the data obtained is in lxml. So, we will parse
            # it with BeautifulSoup library
            soup = BeautifulSoup(decoded_data, "lxml")
            body = soup.body()

            plaintext_messages.append(Message(date, sender, subject, body))
        except Exception as e:
            pass

    return plaintext_messages


def fahrenheit(celcius_temp):
    return ((celcius_temp) * (9/5)) + 32


def mph(kph):
    return kph / 1.609


def inch(centimeter):
    return centimeter / 2.54


def make_fahr_list(row_class_name, value_class_name, weather_soup):
    row = weather_soup.find(class_ = row_class_name)
    temps = row.find_all(class_ = value_class_name)
    forecast_list = []
    for soup in temps:
        forecast_list.append(round(fahrenheit(int(soup.text))))
    return forecast_list


def make_inch_list(row_class_name, value_class_name, weather_soup):
    row = weather_soup.find(class_ = row_class_name)
    temps = row.find_all(class_ = value_class_name)
    forecast_list = []
    for soup in temps:
        if soup.text == '-':
            forecast_list.append('-')
        else:
            forecast_list.append(round(inch(int(soup.text)), 1))
    return forecast_list


def make_wind_list(row_class_name, value_class_name, weather_soup):
    row = weather_soup.find(class_ = row_class_name)
    winds = row.find_all(class_ = value_class_name)
    forecast_list = []
    for soup in winds:
        forecast_list.append(int(soup.text))
    return forecast_list


def make_summary_list(row_class_name, element, weather_soup):
    row = weather_soup.find(class_ = row_class_name)
    summaries = row.find_all(element)
    forecast_list = []
    for soup in summaries:
        summary = soup.text[11:-9]
        forecast_list.append(summary)
    return forecast_list


def site_forecast_start(weather_soup):
    day_row = weather_soup.find(class_ = 'forecast__table-days js-fctable-days')
    day = day_row.td['data-column-name'].replace('_', '')
    time_row = weather_soup.find(class_ = 'forecast__table-time js-fctable-time')
    time = time_row.find(class_ = 'forecast__table-value').text[13:-11]
    first_day_timespan = int(day_row.td['colspan'])
    return day + time, first_day_timespan


def list_forecast_days(weather_soup):
    day_row = weather_soup.find(class_ = 'forecast__table-days js-fctable-days')
    days = []
    for day in day_row.find_all('td'):
        days.append(day['data-column-name'].replace('_', ''))
    return days


def issued_time(weather_soup):
    return weather_soup.find(class_ = 'issued__issued').span.text


def organize_forecast_data(chill_forecast, high_forecast, low_forecast, wind_forecast, snow_forecast, summary_forecast, 
                           forecast_start, forecast_days):
    forecast_data = {}
    forecast_period = 0
    forecast_data[forecast_start[0]] = {}
    forecast_data[forecast_start[0]]['D'] = []
    forecast_data[forecast_start[0]]['H'] = []
    forecast_data[forecast_start[0]]['L'] = []
    forecast_data[forecast_start[0]]['C'] = []
    forecast_data[forecast_start[0]]['W'] = []
    forecast_data[forecast_start[0]]['S'] = []
    for period in range(forecast_start[1]):
        forecast_data[forecast_start[0]]['D'].append(str(summary_forecast[forecast_period]))
        forecast_data[forecast_start[0]]['H'].append(str(high_forecast[forecast_period]))
        forecast_data[forecast_start[0]]['L'].append(str(low_forecast[forecast_period]))
        forecast_data[forecast_start[0]]['C'].append(str(chill_forecast[forecast_period]))
        forecast_data[forecast_start[0]]['W'].append(str(wind_forecast[forecast_period]))
        forecast_data[forecast_start[0]]['S'].append(str(snow_forecast[forecast_period]))
        forecast_period += 1
    for day in forecast_days[1:-1]:
        forecast_data[day] = {}
        forecast_data[day]['D'] = []
        forecast_data[day]['H'] = []
        forecast_data[day]['L'] = []
        forecast_data[day]['C'] = []
        forecast_data[day]['W'] = []
        forecast_data[day]['S'] = []
        for period in range(3):
            forecast_data[day]['D'].append(str(summary_forecast[forecast_period]))
            forecast_data[day]['H'].append(str(high_forecast[forecast_period]))
            forecast_data[day]['L'].append(str(low_forecast[forecast_period]))
            forecast_data[day]['C'].append(str(chill_forecast[forecast_period]))
            forecast_data[day]['W'].append(str(wind_forecast[forecast_period]))
            forecast_data[day]['S'].append(str(snow_forecast[forecast_period]))
            forecast_period += 1
    forecast_data[forecast_days[-1]] = {}
    forecast_data[forecast_days[-1]]['D'] = []
    forecast_data[forecast_days[-1]]['H'] = []
    forecast_data[forecast_days[-1]]['L'] = []
    forecast_data[forecast_days[-1]]['C'] = []
    forecast_data[forecast_days[-1]]['W'] = []
    forecast_data[forecast_days[-1]]['S'] = []
    while forecast_period < 36:
        forecast_data[forecast_days[-1]]['D'].append(str(summary_forecast[forecast_period]))
        forecast_data[forecast_days[-1]]['H'].append(str(high_forecast[forecast_period]))
        forecast_data[forecast_days[-1]]['L'].append(str(low_forecast[forecast_period]))
        forecast_data[forecast_days[-1]]['C'].append(str(chill_forecast[forecast_period]))
        forecast_data[forecast_days[-1]]['W'].append(str(wind_forecast[forecast_period]))
        forecast_data[forecast_days[-1]]['S'].append(str(snow_forecast[forecast_period]))
        forecast_period += 1
    return forecast_data


def no_zeroes(data_pt):
    if '0.' in data_pt:
        return data_pt[1:]
    elif '.0' in data_pt:
        return data_pt[:-2]
    else:
        return data_pt


def forecast_to_sms(forecast, first_day, days, elements, issued, mountain, elevation):
    if 'Mount-' in mountain:
        mountain_abr = mountain[6:11]
    else:
        mountain_abr = mountain[0:5]
    elevation_abr = str(elevation)
    issue_code = (issued[:2] + issued[8:-14]).replace(' ', '') + '\n'
    forecast_sms = [mountain_abr + elevation_abr + ' MF' + issue_code]
    msg = 0
    forecast_sms[msg] += (first_day[0:2] + first_day[3:])
    forecast_sms[msg] += ': '
    for element in elements:
        forecast_sms[msg] += element
        for data in forecast[first_day][element][:-1]:
            forecast_sms[msg] += no_zeroes(data)
            forecast_sms[msg] += '/'
        forecast_sms[msg] += no_zeroes(forecast[first_day][element][-1])
        forecast_sms[msg] += ' '
    forecast_sms[msg] = forecast_sms[msg][:-1]
    forecast_sms[msg] += '\n'
    for day in days[1:]:
        forecast_sms[msg] += (day[0:2] + day[3:])
        forecast_sms[msg] += ': '
        for element in elements:
            forecast_sms[msg] += element
            for data in forecast[day][element][:-1]:
                forecast_sms[msg] += no_zeroes(data)
                forecast_sms[msg] += '/'
            forecast_sms[msg] += no_zeroes(forecast[day][element][-1])
            forecast_sms[msg] += ' '
        forecast_sms[msg] = forecast_sms[msg][:-1]
        if days.index(day) % 2 != 0 and day != days[-1]:
            msg += 1
            forecast_sms.append(mountain_abr + elevation_abr + 'm f' + issue_code)
        elif day != days[-1]:
            forecast_sms[msg] += '\n'
    for message in forecast_sms:
        if len(message) > 160:
            forecast_sms[forecast_sms.index(message)] = message[-148:]
    return forecast_sms


def get_body(msg):
    if msg.is_multipart():
        return get_body(msg.get_payload(0))
    else:
        return msg.get_payload(None, True)


def search(key, value, con):
    result, data = con.search(None, key, '"{}"'.format(value))
    return data


def email_txt(bs4_obj):
    return BeautifulSoup(str(bs4_obj), 'html.parser').get_text()


def get_mtn_fcst_forecast(mountain, elevation, event_log_file):
    # converts mountain request into Mountain-Forecast format
    if mountain in Mountain_Forecast_Peaks:
        mountain = Mountain_Forecast_Peaks[mountain]
    else:
        return ['Mountain requested not found on Mountain-Forecast site. Please refer to requesting guide']

    # converts elevation request into Mountain-Forecast format and tweaks if needed
    if elevation == 'summit':
        elevation = str(Mountain_Forecast_Elevations[mountain][-1])
    elif elevation.isdigit():
        if int(elevation) not in Mountain_Forecast_Elevations[mountain]:
            closest = None
            min_difference = float('inf')
            for avail_elev in Mountain_Forecast_Elevations[mountain]:
                difference = abs(avail_elev - int(elevation))
                if difference < min_difference:
                    closest = avail_elev
                    min_difference = difference
            elevation = str(closest)

    else:
        return ['Elevation requested not understood. Please use <summit> or an elevation listed '
                'in the requesting guide']

    while True:
        try:
            weather_site = requests.get(
                'https://www.mountain-forecast.com/peaks/' + mountain + '/forecasts/' + elevation)
        except requests.exceptions.RequestException as e:
            with open(event_log_file, "a") as file:
                file.write(
                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + 'ERROR getting weather info: ' + str(
                        e) + "\n")

            time.sleep(10)
            continue
        break

    # reads pertinent weather info
    if weather_site.status_code == 200:
        with open(event_log_file, "a") as file:
            file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "GOT WEATHER SITE \n")
        Weather_Soup = BeautifulSoup(weather_site.content, 'html.parser')
        chill_forecast = make_fahr_list('forecast__table-feels', 'forecast__table-value', Weather_Soup)
        # with open(event_log_file, "a") as file:
        #     file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Chill Forecast: " + str(
        #         chill_forecast) + "\n")
        high_forecast = make_fahr_list('forecast__table-max-temperature js-fctable-maxtemp', 'forecast__table-value',
                                       Weather_Soup)
        # with open(event_log_file, "a") as file:
        #     file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "High Forecast: " + str(
        #         high_forecast) + "\n")
        low_forecast = make_fahr_list('forecast__table-min-temperature js-fctable-mintemp', 'forecast__table-value',
                                      Weather_Soup)
        # with open(event_log_file, "a") as file:
        #     file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Low Forecast: " + str(
        #         low_forecast) + "\n")
        wind_forecast = make_wind_list('forecast__table-wind js-fctable-wind', 'wind-icon__val', Weather_Soup)
        # with open(event_log_file, "a") as file:
        #     file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Wind Forecast: " + str(
        #         wind_forecast) + "\n")
        snow_forecast = make_inch_list('forecast__table-snow js-fctable-snow', 'snow', Weather_Soup)
        # with open(event_log_file, "a") as file:
        #     file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Snow Forecast: " + str(
        #         snow_forecast) + "\n")
        summary_forecast = make_summary_list('forecast__table-summary js-fctable-summary', 'td', Weather_Soup)
        # with open(event_log_file, "a") as file:
        #     file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Summary Forecast: " + str(
        #         summary_forecast) + "\n")

        forecast_start = site_forecast_start(Weather_Soup)
        forecast_days = list_forecast_days(Weather_Soup)
        forecast_issued = issued_time(Weather_Soup)

        # organizes weather data
        forecast_data = organize_forecast_data(chill_forecast, high_forecast, low_forecast, wind_forecast,
                                               snow_forecast,
                                               summary_forecast, forecast_start, forecast_days)

        # writes forecast weather data in sms format
        return forecast_to_sms(forecast_data, forecast_start[0], forecast_days, ['H', 'L', 'C', 'W', 'S'],
                               forecast_issued, mountain, elevation)


def get_meteoblue_14_forecast(mountain, event_log_file):
    # converts mountain request into Meteo Blue format
    if mountain in Meteo_Blue_Peaks:
        mountain = Meteo_Blue_Peaks[mountain]
    else:
        return ['Mountain requested not found on Meteo Blue site. Please refer to requesting guide']

    while True:
        try:
            weather_site = requests.get(
                'https://www.meteoblue.com/en/weather/14-days/' + mountain)
        except requests.exceptions.RequestException as e:
            with open(event_log_file, "a") as file:
                file.write(
                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + 'ERROR getting weather info: ' + str(
                        e) + "\n")

            time.sleep(10)
            continue
        break

    # reads pertinent weather info
    if weather_site.status_code == 200:
        with open(event_log_file, "a") as file:
            file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "GOT WEATHER SITE \n")
        weather_soup = BeautifulSoup(weather_site.content, 'html.parser')

        # make forecast with weather site data

        issued = weather_soup.select_one('#header > div > a > div.current-description > span').text.strip()

        days_element = weather_soup.select_one('#content > div > div.col-12 > table > tbody > tr:nth-child(2)')
        days = [cell.get_text(strip=True) for cell in days_element.find_all('td')]

        temps_chart = weather_soup.find(id='canvas_14_days_forecast_tempereture')
        temps_exact_highs = json.loads(temps_chart.get('data-temperatures-max'))
        temps_exact_lows = json.loads(temps_chart.get('data-temperatures-min'))
        temps_highs = [str(round(temp)) for temp in temps_exact_highs]
        temps_lows = [str(round(temp)) for temp in temps_exact_lows]

        predictability_element = weather_soup.select_one(
            '#content > div > div.col-12 > table > tbody > tr:nth-child(8)')
        temp_preds = [cell.get_text(strip=True) for cell in predictability_element.find_all('td')]

        precip_chart = weather_soup.find(id='canvas_14_days_forecast_precipitations')
        precips_exact = json.loads(precip_chart.get('data-precipitation'))
        precips = [no_zeroes(str(round(prec, 2))) for prec in precips_exact]

        precip_probability_element = weather_soup.select_one(
            '#content > div > div.col-12 > table > tbody > tr:nth-child(14)')
        prec_probs = [cell.get_text(strip=True) for cell in precip_probability_element.find_all('td')]

        sms_mb_forecast = make_sms_meteoblue_14(mountain, issued, days, temps_highs, temps_lows, temp_preds, precips,
                                             prec_probs)

        return sms_mb_forecast
    else:
        return ['Failed to get forecast from site. Check request.']


def make_sms_meteoblue_14(mountain, issued, days, temps_highs, temps_lows, temp_preds, precips, prec_probs):
    if 'mount-' in mountain:
        mountain = mountain.split('mount-')[1]

    # builds header that identifies forecast model, peak, and time issued
    header = mountain[:5] + days[0] + 'MB' + issued.split(':')[0] + '\n'

    forecasted_days = []
    for f in range(len(days)):
        forecasted_days.append((days[f] + ':').ljust(6) +
                               ('H' + temps_highs[f]).ljust(4) +
                               ('L' + temps_lows[f]).ljust(5) +
                               ('%' + temp_preds[f].split('%')[0]).ljust(4) +
                               ('P' + precips[f]).ljust(4) +
                               ('%' + prec_probs[f].split('%')[0]).ljust(3))

    texts = ['']
    for d in forecasted_days:
        d += '\n'
        if len(texts[-1]) == 0:
            texts[-1] = header + d
        elif len(texts[-1]) + len(d) > 160:
            texts.append(header + d)
        else:
            texts[-1] += d

    return texts


def get_meteoblue_7_forecast(mountain, event_log_file):
    # converts mountain request into Meteo Blue format
    if mountain in Meteo_Blue_Peaks:
        mountain = Meteo_Blue_Peaks[mountain]
    else:
        return ['Mountain requested not found on Meteo Blue site. Please refer to requesting guide']

    while True:
        try:
            weather_site = requests.get(
                'https://www.meteoblue.com/en/weather/week/' + mountain)
        except requests.exceptions.RequestException as e:
            with open(event_log_file, "a") as file:
                file.write(
                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + 'ERROR getting weather info: ' + str(
                        e) + "\n")

            time.sleep(10)
            continue
        break

    # reads pertinent weather info
    if weather_site.status_code == 200:
        with open(event_log_file, "a") as file:
            file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "GOT WEATHER SITE \n")
        weather_soup = BeautifulSoup(weather_site.content, 'html.parser')

        # make forecast with weather site data

        issued = weather_soup.select_one('#header > div > a > div.current-description > span').text.strip()

        dates_object = weather_soup.select('.tab-day-long')
        dates = []
        for date in dates_object:
            value = date.text.strip()[:5]
            dates.append(value)

        days_object = weather_soup.select('.tab-day-short')
        days = []
        for day in days_object:
            value = day.text.strip()
            days.append(value)

        for d in range(2, 7):
            days[d] = dates[d]

        temps_highs_object = weather_soup.select('.tab-temp-max')
        temps_highs = []
        for temp in temps_highs_object:
            value = temp.text.strip().replace('\xa0°F', '')
            temps_highs.append(value)

        temps_lows_object = weather_soup.select('.tab-temp-min')
        temps_lows = []
        for temp in temps_lows_object:
            value = temp.text.strip().replace('\xa0°F', '')
            temps_lows.append(value)

        winds_object = weather_soup.select('.wind')
        winds = []
        for wind in winds_object:
            value = wind.text.strip().replace(' mph', '')
            winds.append(value)

        precip_object = weather_soup.select('.tab-precip')
        precips = []
        for prec in precip_object:
            value = prec.text.strip().replace('"', '')
            value = no_zeroes(value)
            precips.append(value)

        sun_object = weather_soup.select('.tab-sun')
        clear_hours = []
        for hrs in sun_object:
            value = hrs.text.strip().replace(' h', '')
            clear_hours.append(value)

        pred_selector = [selector for selector in weather_soup.select('[class^="meter-inner predictability"]')]
        preds = []
        for selector in pred_selector:
            value = selector['style'].split('width:')[1].replace('%', '').strip()
            if value == '100':
                value = '99'
            preds.append(value)

        sms_mb_forecast = make_sms_meteoblue_7(mountain, issued, days, temps_highs, temps_lows, winds, precips, clear_hours,
                                             preds)

        return sms_mb_forecast
    else:
        return ['Failed to get forecast from site. Check request.']


def make_sms_meteoblue_7(mountain, issued, days, temps_highs, temps_lows, winds, precips, clear_hrs, preds):
    if 'mount-' in mountain:
        mountain = mountain.split('mount-')[1]
    # builds header that identifies forecast model, peak, and time issued
    header = mountain[:10] + days[0] + 'MB' + issued.split(':')[0] + '\n'

    forecasted_days = []
    for f in range(len(days)):
        forecasted_days.append((days[f] + ':').ljust(6) +
                               ('H' + temps_highs[f]).ljust(4) +
                               ('L' + temps_lows[f]).ljust(5) +
                               ('W' + winds[f]).ljust(6) +
                               ('P' + precips[f]).ljust(6) +
                               ('C' + clear_hrs[f]).ljust(3) +
                               ('%' + preds[f]))

    texts = ['']
    for d in forecasted_days:
        d += '\n'
        if len(texts[-1]) == 0:
            texts[-1] = header + d
        elif len(texts[-1]) + len(d) > 160:
            texts.append(header + d)
        else:
            texts[-1] += d

    return texts


Mountain_Forecast_Peaks = {'Avalanche Spire':       'Avalanche-Spire',
                           'Avalanche':             'Avalanche-Spire',
                           'Avalanche-Spire':       'Avalanche-Spire',
                           'Middle Triple Peak':    'Middle-Triple-Peak',
                           'Middle Triple':         'Middle-Triple-Peak',
                           'Middle-Triple-Peak':    'Middle-Triple-Peak',
                           'Mooses Tooth':          'Mooses-Tooth',
                           'Mooses-Tooth':          'Mooses-Tooth',
                           'Mount Deborah':         'Mount-Deborah',
                           'Deborah':               'Mount-Deborah',
                           'Mount-Deborah':         'Mount-Deborah',
                           'Mount Dickey':          'Mount-Dickey',
                           'Dickey':                'Mount-Dickey',
                           'Mount-Dickey':          'Mount-Dickey',
                           'Sultana':               'Mount-Foraker',
                           'Mount-Foraker':         'Mount-Foraker',
                           'Begguya':               'Mount-Hunter',
                           'Mount Hunter':          'Mount-Hunter',
                           'Hunter':                'Mount-Hunter',
                           'Mount-Hunter':          'Mount-Hunter',
                           'Mount Huntington':      'Mount-Huntington',
                           'Huntington':            'Mount-Huntington',
                           'Mount-Huntington':      'Mount-Huntington',
                           'Denali':                'Mount-McKinley',
                           'Mount McKinley':        'Mount-McKinley',
                           'McKinley':              'Mount-McKinley',
                           'Mount-McKinley':        'Mount-McKinley',
                           'Mount Russell':         'Mount-Russell-Alaska',
                           'Russell':               'Mount-Russell-Alaska',
                           'Mount-Russell-Alaska':  'Mount-Russell-Alaska',
                           'Begguya South Summit':  'Mount-Stevens-Alaska',
                           'Mount Stevens':         'Mount-Stevens-Alaska',
                           'Begguya South':         'Mount-Stevens-Alaska',
                           'Stevens':               'Mount-Stevens-Alaska',
                           'Mount-Stevens-Alaska':  'Mount-Stevens-Alaska',
                           'Mount Silverthrone':    'Silverthrone',
                           'Silverthrone':          'Silverthrone'
                           }

Mountain_Forecast_Elevations = {'Avalanche-Spire': [1000, 2000, 2905],
                                'Middle-Triple-Peak': [1000, 2000, 2693],
                                'Mooses-Tooth': [500, 1500, 2500, 3150],
                                'Mount-Deborah': [1000, 2000, 3000, 3761],
                                'Mount-Dickey': [1000, 2000, 2909],
                                'Mount-Foraker': [500, 1500, 2500, 3500, 4500, 5304],
                                'Mount-Hunter': [500, 1500, 2500, 3500, 4442],
                                'Mount-Stevens-Alaska': [500, 1500, 2500, 3500, 4235],
                                'Mount-Huntington': [1000, 2000, 3000, 3730],
                                'Mount-McKinley': [500, 1500, 2500, 3500, 4500, 5500, 6194],
                                'Mount-Russell-Alaska': [0, 1000, 2000, 3000, 3557],
                                'Silverthrone': [500, 1500, 2500, 3500, 4030]}

Meteo_Blue_Peaks = {'Begguya': 'mount-hunter_united-states_5864415',
                    'SE Fork Kahiltna': 'southeast-fork-kahiltna-glacier_united-states_5874864',
                    'Begguya South': 'mount-stevens_united-states_8096104',
                    'E Fork Kahiltna': 'east-fork-kahiltna-glacier_united-states_5861274',
                    'Kahiltna Peaks': 'kahiltna-peaks_united-states_5865628',
                    'Browne Tower': 'browne-tower_united-states_5858099',
                    'Mount Capps': 'mount-capps_united-states_5858636',
                    'Carter Horn': 'carter-horn_united-states_5858754',
                    'Mount Crosson': 'mount-crosson_united-states_5860146',
                    'Mount Dan Beard': 'mount-dan-beard_united-states_5860303',
                    'Mount Dickey': 'mount-dickey_united-states_5860678',
                    'East Buttress': 'east-buttress_united-states_5861230',
                    'Farthing Horn': 'farthing-horn_united-states_5861992',
                    'Foraker Glacier': 'foraker-glacier_united-states_5862340',
                    'Sultana': 'mount-foraker_united-states_5862350',
                    'Harper Icefall': 'harper-icefall_united-states_5863720',
                    'Harper Glacier': 'harper-glacier_united-states_5863727',
                    'Mount Huntington': 'mount-huntington_united-states_5864420',
                    'Kahiltna Dome': 'kahiltna-dome_united-states_5865625',
                    'Kahiltna Glacier': 'kahiltna-glacier_united-states_5865630',
                    'Denali': 'denali_united-states_5868589',
                    'North Peak': 'north-peak_united-states_5870285',
                    'NW Fork Ruth': 'northwest-fork-ruth-glacier_united-states_5870356',
                    'NE Fork Kahiltna': 'northeast-fork-kahiltna-glacier_united-states_5870363',
                    'Pease Peak': 'pease-peak_united-states_5871357',
                    'Peters Basin': 'peters-basin_united-states_5871464',
                    'Peters Glacier': 'peters-glacier_united-states_5871469',
                    'Rooster Comb': 'the-rooster-comb_united-states_5872944',
                    'South Peak': 'south-peak_united-states_5874834',
                    'Straightaway Glacier': 'straightaway-glacier_united-states_5875271',
                    'Traleika Icefall': 'traleika-icefall_united-states_5876573',
                    'W Fork Ruth': 'west-fork-ruth-glacier_united-states_5877826',
                    'Wickersham Wall': 'wickersham-wall_united-states_5878039',
                    'Mount Barrille': 'mount-barrille_united-states_5880046',
                    'Herron Glacier': 'herron-glacier_united-states_5863955',
                    'Mount Church': 'mount-church_united-states_5859407',
                    'Explorers Peak': 'explorers-peak_united-states_5861878',
                    'Glacier Point': 'glacier-point_united-states_5846682',
                    'Mount Koven': 'mount-koven_united-states_5866736',
                    'Mooses Tooth': 'mooses-tooth_united-states_5869283',
                    'N Fork Ruth': 'north-fork-ruth-glacier_united-states_5870248',
                    'Mount Silverthrone': 'mount-silverthrone_united-states_5874207',
                    'Archdeacons Tower': 'archdeacons-tower_united-states_5879607',
                    'Mount Sholes': 'mount-sholes_united-states_5874053',
                    'Buckskin Glacier': 'buckskin-glacier_united-states_5858183',
                    'Mount Mazama': 'mount-mazama_united-states_5868481',
                    'Mount Glisen': 'mount-glisen_united-states_5862937',
                    'Lacuna Glacier': 'lacuna-glacier_united-states_5867043',
                    'Tokositna Glacier': 'tokositna-glacier_united-states_5876380',
                    'Gurney Peak': 'gurney-peak_united-states_5863556',
                    'Kichatna Mountains': 'kichatna-mountains_united-states_5866158',
                    'Cathedral Spires': 'cathedral-spires_united-states_5858857',
                    'Lewis Peak': 'lewis-peak_united-states_5867320',
                    'Caldwell Glacier': 'caldwell-glacier_united-states_5858377',
                    'Shelf Glacier': 'shelf-glacier_united-states_5873937',
                    'Tatina Glacier': 'tatina-glacier_united-states_5875869',
                    'Augustin Peak': 'augustin-peak_united-states_5879781',
                    'Shadows Glacier': 'shadows-glacier_united-states_5873785',
                    'Cul-de-sac Glacier': 'cul-de-sac-glacier_united-states_5860203'
                    }

# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Get the path of the directory that contains this Python file
dir_path = os.path.dirname(os.path.realpath(__file__))

# secret authorization file from google. copy paste filename of json in program location
Secret_File = os.path.join(dir_path, 'client_secret_114502949276-96f9b62a390e495jh6mscm5cjbhlf6nu.apps.googleusercontent.com.json')

default_ignore_previous_to = 'Wed, 19 Apr 2023 20:39:33 -0400'
# forecast_email = 'dewey.mtn.forecasts@gmail.com'
# forecast_email_password = 'xPQ2Sups@Zq3SU64#7%Wul!2kh%XSEM6'
# imap_url = 'imap.gmail.com'
# inreach_from_email = 'no.reply.inreach@garmin.com'
# inreach_email = 'ben437B4@inreach.garmin.com'
default_mountain = "Mount-Hunter"
default_elevation = '4442'

read_log_file = os.path.join(dir_path, "previously_read_log.txt")

event_log_file = os.path.join(dir_path, 'event_logs/event_log_' + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + '.txt')

#gives Raspi time to establish connection
time.sleep(10)

# Creates event log if none exists
with open(event_log_file, "w") as file:
    file.write("EVENT LOG:\n")

# Opens log of date to ignore prior emails and sets previously read date to that
try:
    with open(read_log_file, "r") as file:
        # Read the contents of the file into a variable
        ignore_previous_to = file.read()
    print("Ignoring emails previous to: ", ignore_previous_to)
# If the file does not exist, create it and set it's contents to the default previously read date
except FileNotFoundError:
    print(f"{read_log_file} does not exist. Creating it now...")
    with open(read_log_file, "w") as file:
        file.write(default_ignore_previous_to)
    with open(read_log_file, "r") as file:
        # Read the contents of the file into a variable
        ignore_previous_to = file.read()
    print("Ignoring emails previous to: ", ignore_previous_to)

while True:
    try:
        print("\rchecking for forecast requests...", ' '*20, end='')
        # retrieves messages from gmail
        msgs = retrieve_emails(Secret_File, 50)

        # makes list of messages that are forecast requests and new
        requested_forecasts = []
        for msg in msgs:
            if mktime_tz(parsedate_tz(msg.date)) > mktime_tz(parsedate_tz(ignore_previous_to)):
                if 'get forecast' in email_txt(msg.body):
                    requested_forecasts.append(msg)

        # takes action for each forecast request
        for request in requested_forecasts:
            with open(event_log_file, "a") as file:
                file.write("\n")
            # checks if it's a test
            test = False
            if '~test~' in email_txt(request.body):
                test = True
                with open(event_log_file, "a") as file:
                    file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "the following request is a test:\n")

            # sets model, mountain and elevation, default if parameters not met
            with open(event_log_file, "a") as file:
                file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "REQUEST RECEIVED at " + str(request.date) + "\n")
            model = "meteoblue7"
            print(email_txt(request.body))
            if 'model: $' in email_txt(request.body):
                indexstart = email_txt(request.body).find('model: $') + 8
                indexend = email_txt(request.body)[indexstart:].find('$') + indexstart
                model = email_txt(request.body)[indexstart:indexend]
                with open(event_log_file, "a") as file:
                    file.write(
                        datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Model: " + model + "\n")
            mountain = default_mountain
            if 'mountain: $' in email_txt(request.body):
                indexstart = email_txt(request.body).find('mountain: $') + 11
                indexend = email_txt(request.body)[indexstart:].find('$') + indexstart
                mountain = email_txt(request.body)[indexstart:indexend]
                with open(event_log_file, "a") as file:
                    file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                               + '      ' + 'Mountain: ' + mountain + '\n')
            elevation = default_elevation
            if 'elevation: $' in email_txt(request.body):
                indexstart = email_txt(request.body).find('elevation: $') + 12
                indexend = email_txt(request.body)[indexstart:].find('$') + indexstart
                elevation = email_txt(request.body)[indexstart:indexend]
                with open(event_log_file, "a") as file:
                    file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                               + "      " + "Elevation: " + elevation + "\n")
            if not test:
                print('\r' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "REQUEST RECEIVED for "
                      + model + '\'s forecast of ' + mountain + ' at ' + elevation + ' elevation')
            elif test:
                print('\r' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "TEST REQUEST RECEIVED for "
                      + model + '\'s forecast of ' + mountain + ' at ' + elevation + ' elevation')

            # gets weather info
            print("\rretrieving forecast...", ' '*20, end='')
            if model == 'mountain-forecast':
                sms_forecast = get_mtn_fcst_forecast(mountain, elevation, event_log_file)
            elif model == 'meteoblue14':
                sms_forecast = get_meteoblue_14_forecast(mountain, event_log_file)
            elif model == 'meteoblue7':
                sms_forecast = get_meteoblue_7_forecast(mountain, event_log_file)
            else:
                sms_forecast = ['model site request not understood. please use either \"model: $mountain-forecast$\" '
                                'or \"model: $meteoblue7$\" or \"model: $meteoblue14$\"']

            print("\r", ' '*40, end='')
            print('\r' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "WEATHER MESSAGES:\n")
            for msg in sms_forecast:
                print(msg)
            with open(event_log_file, "a") as file:
                for msg in sms_forecast:
                    file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                               + '      ' + msg)

            print("\rsending forecast to inreach...", ' ' * 20, end='')
            # sends sms data to inreach
            port = 465
            while True:
                try:
                    options = webdriver.ChromeOptions()
                    options.add_argument('--ignore-certificate-errors')
                    options.add_argument("--test-type")
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    driver = webdriver.Chrome(options=options)
                    mapshare_address = 'https://share.garmin.com/VGTRY'
                    for message in sms_forecast:
                        for i in range(30):
                            try:
                                driver.get(mapshare_address)
                                driver.implicitly_wait(60)
                                try:
                                    close_button = driver.find_elements_by_xpath(
                                        '//*[@id="inreach-right-ad-close"]')[0]
                                    close_button.click()
                                    driver.implicitly_wait(30)
                                except Exception as e:
                                    pass
                                message_button = driver.find_elements_by_xpath('//*[@id="user-messaging-controls"]/div[2]')[0]
                                message_button.click()
                                driver.implicitly_wait(40)
                                from_email_text_area = driver.find_elements_by_xpath('//*[@id="messageFrom"]')[0]
                                from_email_text_area.send_keys('dewey.mtn.forecasts@gmail.com')
                                msg_text_area = driver.find_elements_by_xpath('//*[@id="textMessage"]')[0]
                                msg_text_area.send_keys(message)
                                driver.implicitly_wait(20)
                                if not test:
                                    send_button = driver.find_elements_by_xpath('//*[@id="divModalMessage"]/div/div/div[3]/div[2]/button[2]')[0]
                                    send_button.click()
                                    driver.implicitly_wait(8)
                                time.sleep(5)
                                with open(event_log_file, "a") as file:
                                    if not test:
                                        file.write(datetime.now().strftime(
                                            "%m/%d/%Y, %H:%M:%S") + "      " + "Message Sent: " + str(
                                            message) + "\n")
                                        print('\r' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "message sent")
                                    elif test:
                                        file.write(datetime.now().strftime(
                                            "%m/%d/%Y, %H:%M:%S") + "      " + "Test Message Successful" + "\n")
                                        print('\r' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "test message successful")
                            except Exception as e:
                                with open(event_log_file, "a") as file:
                                    file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "Error with Garmin website: " + str(e) + "\n")
                                continue
                            break
                    driver.close()
                # if error
                except Exception as e:
                    with open(event_log_file, "a") as file:
                        file.write(
                            datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + 'ERROR sending messages: ' + str(e) + "\n")
                    time.sleep(1)
                    continue
                last_sent = datetime.now()
                break

        # updates latest message log
        for request in requested_forecasts:
            if mktime_tz(parsedate_tz(request.date)) > mktime_tz(parsedate_tz(ignore_previous_to)):
                ignore_previous_to = request.date
                with open(read_log_file, "w") as file:
                    file.write(ignore_previous_to)
                print('\r' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "now ignoring emails previous to " + ignore_previous_to)

        # waits 5 minutes
        for i in range(300):
            message = f"\rnext check in {(300-i)} seconds..."
            print(message, ' '*20, end="\r")
            time.sleep(1)

    except Exception as e:
        with open(event_log_file, "a") as file:
            file.write(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + 'ERROR: ' + str(e) + "\n")
        if e.args[0]['status'] == '429':

            (datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + "      " + "user rate limit exceeded when attempting to retrieve emails")
            for i in range(910):
                message = f"\rnext check in {(910 - i)} seconds..."
                print(message, ' '*20, end="\r")
                time.sleep(1)
        else:
            for i in range(60):
                message = f"\rnext check in {(60 - i)} seconds..."
                print(message, ' '*20, end="\r")
                time.sleep(1)
        continue
