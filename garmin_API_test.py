import requests
from base64 import b64encode
import json
from dotenv import load_dotenv
import os
import logging
from bs4 import BeautifulSoup


def configure():
    load_dotenv()


def basic_auth(username, password):
    token = token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'


def send_to_inreach(msg, api_url, username, password):
    headers = { 'Authorization' : basic_auth(username, password) }
    body = {"messages": msg}
    response = requests.post(api_url, headers=headers, params=body)
    return response


# configure()

# garmin_username = os.getenv('IPC_USER_NAME')
# garmin_password = os.getenv('IPC_PASSWORD')
# garmin_ipc_address = 'https://us0-enterprise.inreach.garmin.com/IPCInbound'
# messaging_url = '/V1/Messaging.svc'


# garmin_address = garmin_ipc_address + messaging_url + '/Message'
# response = send_to_inreach(msg, garmin_address, garmin_username, garmin_password)
# response.raise_for_status()

# results = response.json()
# print(json.dumps(results))

def create_map_share_payload(url, text):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    message_id = soup.find("input", {"id": "MessageId"}).get('value')
    guid = soup.find("input", {"id": "Guid"}).get('value')
    reply_address = soup.find("input", {"id": "ReplyAddress"}).get('value')

    return {'ReplyAddress': reply_address,
            'ReplyMessage': text,
            'MessageId': message_id,
            'Guid': guid}

def notify_map_share(url, text):
    payload = create_map_share_payload(url, text)
    logging.debug(payload)

    session = requests.Session()
    response = session.post(
        'https://us0.explore.garmin.com/textmessage/txtmsg',
        headers={'User-Agent': 'Mozilla/5.0'},
        data=payload)

    logging.info(response.headers)

map_share_url = 'https://us0.explore.garmin.com/textmessage/txtmsg?extId=08db5496-6f20-9f8e-000d-3aa7780f0000&adr=dewey.mtn.forecasts%40gmail.com'
forecast_text = 'this is a test from 3/25'

logging.basicConfig(level=logging.DEBUG)
notify_map_share(map_share_url, forecast_text)

# def basic_auth(username, password):
#     token = token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
#     return f'Basic {token}'


# def send_to_inreach(msg, api_url, username, password):
#     #api_url = 'https://us0-origin.explore.garmin.com:443/ipcinbound/V1/Messaging.svc/Message'
#     headers = { 'Authorization' : basic_auth(username, password) }
#     body = {
#             "Messages": [
#                 {
#                 "Recipients": [
#                     "300434063854220"
#                 ],
#                 "Sender": "dewey.mtn.forecasts@gmail.com",
#                 "Timestamp": "\/Date(" + str(int(time.time()*1000)) + ")\/",
#                 "Message": msg,
#                 "ReferencePoint": {
#                     "LocationType": "ReferencePoint",
#                     "Altitude": 0,
#                     "Speed": 0,
#                     "Course": 0,
#                     "Coordinate": {
#                     "Latitude": 0,
#                     "Longitude": 0
#                     },
#                     "Label": "none"
#                 }
#                 }
#             ]
#             }
#     response = requests.post(api_url, headers=headers, params=body)
#     response.raise_for_status()
#     return response.json()