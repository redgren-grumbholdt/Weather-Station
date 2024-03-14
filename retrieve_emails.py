from bs4 import BeautifulSoup
import time
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
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
            print(soup)
            body = soup.body()

            plaintext_messages.append(Message(date, sender, subject, body))
        except Exception as e:
            pass

    return plaintext_messages


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


# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Get the path of the directory that contains this Python file
dir_path = os.path.dirname(os.path.realpath(__file__))

# secret authorization file from google. copy paste filename of json in program location
Secret_File = os.path.join(dir_path, 'client_secret_114502949276-qujopcn3v6e65fdkjm1f7mikmdcicbad.apps.googleusercontent.com.json')

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
        
        print(msgs)

        # makes list of messages that are forecast requests and new
        requested_forecasts = []
        for msg in msgs:
            if mktime_tz(parsedate_tz(msg.date)) > mktime_tz(parsedate_tz(ignore_previous_to)):
                if 'get forecast' in email_txt(msg.body):
                    requested_forecasts.append(msg)
    
        print(requested_forecasts)

        time.sleep(60)

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