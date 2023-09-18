# Google Calendar API to Discord Webhook Example
#
# Author: SquishyMona
# GitHub: https://github.com/SquishyMona
#
# Through all my Google searching, I wasn't able to find any cost effective and simple solutions to send Google Calendar
# notifications to Discord. This solution is something I cam up with using various bits of knowledge I found on the
# internet, and I hope it helps anyone out there who want's to do something like this. I'm sure this can be optimized
# and adapted more to fit your own needs, but here's a quick example of how to get started.
#
# This method uses Firebase Cloud Functions written in Python. Firebase gives you 2 million(?) free invocations per
# month, which is plenty for me, and most likely the majority of use cases. Head over to the Firebase website for a
# tutorial on how to set up your CLI setup and project created. Once you have all that done, you'll be able to deploy
# this function and use the URL it gives you to set up your Google Calendar API push notifications.

from firebase_functions import https_fn, options
from firebase_admin import initialize_app
from googleapiclient.discovery import build
from discord_webhook import DiscordWebhook, DiscordEmbed
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dateutil import parser as dtparse
import json
import dotenv
import os

dotenv.load_dotenv()

# Defining some globals. Service account file should be located in the same directory as this file.
# Resource IDs are used to identify which webhook to send to.
#
# You can redefine scopes to your purpose, or get rid of this ouright if you don't need it. For Google APIs, we'll need this.
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'your_file_here.json'

credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# This function will run when a 'watch' request is made to the API. Whatever URL Firebase gives you when you deploy your
# function will be the URL you give to the 'watch' request. When you make that request, a sync message is sent to this function
# and all other times, it will be your push notification from Google.
@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]))
def on_request_example(req: https_fn.Request) -> https_fn.Response:
    service = build('calendar', 'v3', credentials=credentials)

    # These lines aren't needed, but can be used to run multiple webhooks from this same function. In my case, I have 3
    # webhooks set up, and since all messages will look the same, just with different info, this approach works great.
    if req.headers.get('x-goog-resource-id') == os.getenv('ACAPELLA_RESOURCEID'):
        calendarId = os.getenv('ACAPELLA_CAL_ID')
        webhookurl = os.getenv('ACAPELLA_WEBHOOK')
        token = 'acapella'
    if req.headers.get('x-goog-resource-id') == os.getenv('SLIH_REH_RESOURCEID'):
        calendarId = os.getenv('SLIH_REH_CAL_ID')
        webhookurl = os.getenv('SLIH_REH_WEBHOOK')
        token = 'slih_reh'
    if req.headers.get('x-goog-resource-id') == os.getenv('SLIH_GIGS_RESOURCEID'):
        calendarId = os.getenv('SLIH_GIGS_CAL_ID')
        webhookurl = os.getenv('SLIH_GIGS_WEBHOOK')
        token = 'slih_gigs'
    
    # When we get a sync notification, we'll need to get new sync tokens to use in our subsequent requests. The sync
    # tokens are used to make sure when we run the 'list' request, we only get the events that have changed since the
    # last listing. The sync notiiciation is the perfect time to grab our first sync token. We'll store it in a JSON
    # file so we can get the updated tokens later. 

    if req.headers.get('x-goog-resource-state') == 'sync':
        with open('synctoken.json') as json_file:
            nextSyncToken = json.load(json_file)
        print(f"Sync event received, channel started for id {req.headers.get('x-goog-resource-id')}")
        events_result = service.events().list(calendarId=calendarId).execute()
        nextSyncToken[token] = events_result['nextSyncToken']
        print(f'The next sync token is {events_result["nextSyncToken"]} for calendar {token}')
        with open('synctoken.json', 'w') as outfile:
            json.dump(nextSyncToken, outfile)
        return https_fn.Response("Sync event received")
    
    # If the event is not a sync notification, something has changed on one of our calendars.
    else:
        print("Changes detected.")
        with open('synctoken.json') as json_file:
            nextSyncToken = json.load(json_file)
        events_result = service.events().list(calendarId=calendarId, syncToken=nextSyncToken[token]).execute()
        nextSyncToken[token] = events_result['nextSyncToken']
        # In case our JSON file fails, we'll print the next sync token to our console in case we need to manually specify it.
        print(f'The next sync token is {events_result["nextSyncToken"]} for calendar {token}')
        with open('synctoken.json', 'w') as outfile:
            json.dump(nextSyncToken, outfile)
        events = events_result.get('items', [])

        for event in events:
            # If an event has 'confirmed' status, we need to check if it's a new event, or an existing event that's
            # been updated. In this case, we'll check the 'created' and 'updated' fields to see if they're the same.
            # This might not be completely accurate, as there's a millisecond difference between 'created' and 'updated'
            # when an event is created, but it's the best we can do for now. To help this fact, we'll also cut the
            # milliseconds from our calculations. After all this, the notification will be sent to our Discord webhook
            if event['status'] == 'confirmed':
                if int(dtparse.parse(event['created']).strftime('%Y%m%d%H%M%S')) != int(dtparse.parse(event['updated']).strftime('%Y%m%d%H%M%S')):
                    print(f"An event on calendar {token} has been updated. Debug Info:\n\n{event}")
                    webhook = DiscordWebhook(url=webhookurl, content="An event has been updated!")
                    embed = DiscordEmbed(title=event['summary'], description=f'[View on Google Calendar]({event["htmlLink"]})', color=242424)
                    embed.set_author(name='Google Calendar', icon_url='https://uxwing.com/wp-content/themes/uxwing/download/brands-and-social-media/google-calendar-icon.png')
                    embed.add_embed_field(name='Date', value=dtparse.parse(event['start']['dateTime']).strftime('%B %d, %Y'), inline=False)
                    embed.add_embed_field(name='Start Time', value=dtparse.parse(event['start']['dateTime']).strftime('%-I:%M %p'))
                    embed.add_embed_field(name='End Time', value=dtparse.parse(event['end']['dateTime']).strftime('%-I:%M %p'))
                    try:
                        embed.add_embed_field(name='Location', value=event['location'], inline=False)
                    except KeyError:
                        pass
                    try:
                        embed.add_embed_field(name='Description', value=event['description'], inline=False)
                    except KeyError:
                        pass
                    webhook.add_embed(embed)
                    webhook.execute()
                else: 
                    print(f"A new event on calendar {token} has been added. Debug Info:\n\n{event}")
                    webhook = DiscordWebhook(url=webhookurl, content="A new event has been added!")
                    embed = DiscordEmbed(title=event['summary'], description=f'[View on Google Calendar]({event["htmlLink"]})', color=242424)
                    embed.set_author(name='Google Calendar', icon_url='https://uxwing.com/wp-content/themes/uxwing/download/brands-and-social-media/google-calendar-icon.png')
                    embed.add_embed_field(name='Date', value=dtparse.parse(event['start']['dateTime']).strftime('%B %d, %Y'), inline=False)
                    embed.add_embed_field(name='Start Time', value=dtparse.parse(event['start']['dateTime']).strftime('%-I:%M %p'))
                    embed.add_embed_field(name='End Time', value=dtparse.parse(event['end']['dateTime']).strftime('%-I:%M %p'))
                    try:
                        embed.add_embed_field(name='Location', value=event['location'], inline=False)
                    except KeyError:
                        pass
                    try:
                        embed.add_embed_field(name='Description', value=event['description'], inline=False)
                    except KeyError:
                        pass
                    webhook.add_embed(embed)
                    webhook.execute()
            # If an event has 'cancelled' status, we'll send a notification to Discord that the event has been cancelled.
            elif event['status'] == 'cancelled':
                print(f"An event on calendar {token} has been removed. Debug Info:\n\n{event}")
                cancelledevent = service.events().get(calendarId=calendarId, eventId=event['id']).execute()
                webhook = DiscordWebhook(url=webhookurl, content="An event has been cancelled!")
                embed = DiscordEmbed(title=cancelledevent['summary'], color=242424)
                embed.set_author(name='Google Calendar', icon_url='https://uxwing.com/wp-content/themes/uxwing/download/brands-and-social-media/google-calendar-icon.png')
                embed.add_embed_field(name='Date', value=dtparse.parse(cancelledevent['start']['dateTime']).strftime('%B %d, %Y'), inline=False)
                embed.add_embed_field(name='Start Time', value=dtparse.parse(cancelledevent['start']['dateTime']).strftime('%-I:%M %p'))
                embed.add_embed_field(name='End Time', value=dtparse.parse(cancelledevent['end']['dateTime']).strftime('%-I:%M %p'))
                try:
                    embed.add_embed_field(name='Location', value=cancelledevent['location'], inline=False)
                except KeyError:
                    pass
                try:
                    embed.add_embed_field(name='Description', value=cancelledevent['description'], inline=False)
                except KeyError:
                    pass
                webhook.add_embed(embed)
                webhook.execute()
                
        return https_fn.Response("Request fulfilled.")