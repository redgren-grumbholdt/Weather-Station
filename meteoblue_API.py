import datetime as dt
import requests

BASE_URL = "https://my.meteoblue.com/packages/basic-1h_basic-day_clouds-3h_clouds-day_trendpro-day?"
METEOBLUE_API_KEY = secrets.METEOBLUE_API_KEY
LOCATION = "lat=62.920&lon=-151.070"
ELEVATION = ""

url = BASE_URL + METEOBLUE_API_KEY + "&" + LOCATION + "&"
if ELEVATION != "":
    url.append("&")
url.append("format=json")

response = requests.get(url).json()

print(response)