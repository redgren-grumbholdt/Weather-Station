import datetime as dt
import requests
import json
from dotenv import load_dotenv
import os

FORECAST_FILE = "recent_forecast.json"
BASE_URL = "https://my.meteoblue.com/packages/basic-1h_clouds-1h_trendpro-day"
LOCATION = "lat=62.920&lon=-151.070"
ELEVATION = ""


def configure():
    load_dotenv()


def main():
    configure()

    url = BASE_URL + "?apikey=" + os.getenv('METEOBLUE_API_KEY') + "&" + LOCATION + "&"
    if ELEVATION != "":
        url += "&"
    url += "format=json&temperature=F&windspeed=mph&precipitationamount=inch&winddirection=2char"

    response = requests.get(url).json()

    with open(FORECAST_FILE, "w") as file:
        json.dump(response, file)

    print(response)

main()