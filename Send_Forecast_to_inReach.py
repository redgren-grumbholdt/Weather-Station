import json
import os

FORECAST_FILE = "recent_forecast.json"
Forecast = {}


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


def main():
    with open(FORECAST_FILE, 'r') as file:
        Forecast = json.load(file)
    day_forecast = ''.join(format_day_forecast(Forecast['trend_day'], '18'))
    print(day_forecast)
    print(len(day_forecast))
    print('\n')
    sixhr_forecast = ''.join(format_6hr_forecast(Forecast['data_1h'], '18 00'))
    print(sixhr_forecast)
    print(len(sixhr_forecast))

main()