import datetime as dt
import requests
import json
from dotenv import load_dotenv

BASE_URL = "https://my.meteoblue.com/packages/basic-3h_basic-day_clouds-3h_trend-day"
LOCATION = "lat=62.920&lon=-151.070"
ELEVATION = ""

url = BASE_URL + "?apikey=" + METEOBLUE_API_KEY + "&" + LOCATION + "&"
if ELEVATION != "":
    url += "&"
url += "format=json"

print(url)
response = requests.get(url).json()

with open("recent_forecast.json", "w") as file:
    json.dump(response, file)

print(response)