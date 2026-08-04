from icalendar import Calendar, Event
import requests
from zoneinfo import ZoneInfo
import datetime
import time
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

airbnb_ical = os.environ.get("AIRBNB_ICAL")
booking_ical = os.environ.get("BOOKING_ICAL")
gcal = os.environ.get("GOOGLE_CAL_ID")
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def delete_event(title):
    creds = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    service = build("calendar", "v3", credentials=creds)

    events = service.events().list(
        calendarId=gcal,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    for event in events.get("items", []):

        if event.get("summary") == title:
            service.events().delete(
                calendarId=gcal,
                eventId=event["id"]
            ).execute()
            print('deleted')
            return

    return

def modify_event(new_start, new_end, title):
    creds = Credentials.from_authorized_user_file(
        "token.json",
        SCOPES
    )

    service = build("calendar", "v3", credentials=creds)

    events = service.events().list(
        calendarId=gcal,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    for event in events.get("items", []):

        if event.get("summary") == title:
            event["start"]["dateTime"] = new_start
            event["end"]["dateTime"] = new_end

            service.events().update(
                calendarId=gcal,
                eventId=event["id"],
                body=event
            ).execute()
            return

    return

def create_event(start, end, title):
    # 1. Setup Service & Authenticate (creates/uses token.json)
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # 2. Define the Event
    event = {
        'summary': title,
        'start': {'dateTime': start, 'timeZone': 'America/New_York'},
        'end': {'dateTime': end, 'timeZone': 'America/New_York'},
    }

    # 3. Insert Event
    event = service.events().insert(calendarId=gcal, body=event).execute()


if __name__ == '__main__':
    """
    Pull iCal events from airbnb, booking.com, and hostshare if possible
    Pull all events on the google calendar
    Iterate through events: if it is on the ical but not google calendar, add it
    if it is on the google calendar but not ical, remove it
    if it is on both check dates,
    if they match pass, if they dont update 
    '2024-12-31T11:00:00' this is the date format google calendar uses
    
    """

    '''
    Google Calendar
    '''
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("calendar", "v3", credentials=creds)
    gcal_events = service.events().list( calendarId=gcal, singleEvents=True,orderBy="startTime").execute()
    gcal_titles = []
    for event in gcal_events.get("items", []):
        gcal_titles.append(event.get("summary"))

    '''
    Airbnb
    '''

    response = requests.get(airbnb_ical).text
    airbnb_ical = Calendar.from_ical(response)
    ical_titles = []

    for event in airbnb_ical.walk("VEVENT"):
        if event.get("summary") == 'Reserved':
            title = event.get("uid")
            ical_titles.append(title)
            if title not in gcal_titles:

                start = str(event.get("dtstart").dt) + 'T15:00:00'
                end = str(event.get("dtend").dt) + 'T11:00:00'
                create_event(start, end, title)
                gcal_titles.append(title)
            else:
                need_update = False
                ind = gcal_titles.index(title)
                gcal_event = gcal_events.get("items", [])[ind]
                gcal_start_date = gcal_event.get("start").get("dateTime")
                gcal_end_date = gcal_event.get("end").get("dateTime")

                airbnb_ical_start_date_raw = datetime.fromisoformat(str(event.get("dtstart").dt))
                airbnb_ical_start_date = str(airbnb_ical_start_date_raw.replace(tzinfo=ZoneInfo("America/New_York"), hour=15)).replace(' ','T')
                airbnb_ical_end_date_raw = datetime.fromisoformat(str(event.get("dtend").dt))
                airbnb_ical_end_date = str(airbnb_ical_end_date_raw.replace(tzinfo=ZoneInfo("America/New_York"), hour=11)).replace(' ','T')

                if gcal_start_date != airbnb_ical_start_date:
                    gcal_start_date = airbnb_ical_start_date
                    need_update = True
                if gcal_end_date != airbnb_ical_end_date:
                    gcal_end_date = airbnb_ical_end_date
                    need_update = True
                if need_update:
                    modify_event(gcal_start_date, gcal_end_date, title)
                    need_update = False
    '''
    booking.com 
    '''
    response = requests.get(booking_ical).text
    booking_ical = Calendar.from_ical(response)
    for event in booking_ical.walk("VEVENT"):
        title = event.get("uid")
        ical_titles.append(title)
        if title not in gcal_titles:

            start = str(event.get("dtstart").dt) + 'T15:00:00'
            end = str(event.get("dtend").dt) + 'T11:00:00'
            create_event(start, end, title)
            gcal_titles.append(title)
        else:
            need_update = False
            ind = gcal_titles.index(title)
            gcal_event = gcal_events.get("items", [])[ind]
            gcal_start_date = gcal_event.get("start").get("dateTime")
            gcal_end_date = gcal_event.get("end").get("dateTime")

            booking_ical_start_date_raw = datetime.fromisoformat(str(event.get("dtstart").dt))
            booking_ical_start_date = str(booking_ical_start_date_raw.replace(tzinfo=ZoneInfo("America/New_York"), hour=15)).replace(' ', 'T')
            booking_ical_end_date_raw = datetime.fromisoformat(str(event.get("dtend").dt))
            booking_ical_end_date = str(booking_ical_end_date_raw.replace(tzinfo=ZoneInfo("America/New_York"), hour=11)).replace(' ', 'T')

            if gcal_start_date != booking_ical_start_date:
                gcal_start_date = booking_ical_start_date
                need_update = True
            if gcal_end_date != booking_ical_end_date:
                gcal_end_date = booking_ical_end_date
                need_update = True
            if need_update:
                modify_event(gcal_start_date, gcal_end_date, title)
                need_update = False


    '''
    Checking for events to delete
    '''
    if len(gcal_titles) > len(ical_titles):
        for event in gcal_events.get("items", []):
            title = event.get("summary")
            if title not in ical_titles:
                delete_event(title)



