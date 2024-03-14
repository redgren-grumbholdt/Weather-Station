import datetime as dt
import requests
import json
from dotenv import load_dotenv
import os

BASE_URL = "https://my.meteoblue.com/packages/basic-3h_basic-day_clouds-3h_trend-day"
LOCATION = "lat=62.920&lon=-151.070"
ELEVATION = ""


def configure():
    load_dotenv()


def main():
    configure()

    url = BASE_URL + "?apikey=" + os.getenv('METEOBLUE_API_KEY') + "&" + LOCATION + "&"
    if ELEVATION != "":
        url += "&"
    url += "format=json"

    response = requests.get(url).json()

    with open("recent_forecast.json", "w") as file:
        json.dump(response, file)

    print(response)

main()