# Google Calendar API To Discord Webhook
## A simple example of using the Google Calendar API to send calendar updates to Discord webhooks

## What We're Using
- Firebase Cloud Functions
- Python 3.11
- Google Calendar API v3

## How It Works
Google Calendar's API includes 'watch' requests for various resources, such as events, calendars, etc. When you make a watch request to the API, it opens up a channel which watches for changes on the resources specified (in our example, we watch for events). If the resource changes, then Google sends a push notification to the channel URl you specify in the watch request. In this case, we specify our channel URL as the URL to our Firebase Function. Some examples have tried utilizing a Google Apps Script (GAS) web app to achieve the goal, but for some odd reason, GAS doesn't let you access HTTP headers when the doPost method, or any method, is run. This is inconvinient for us because, unfortunately, all the (very little) useful information we need from the HTTP request are in the headers. For this reason, a completely free solution with GAS isn't possible, but Firebase Cloud Functions comes very close, since it gives you 2 million free function invocations per month. The other problem we have is that Google's push notifications aren't very useful, only telling you that something has changed, but not what specifically. To solve this, we create a function that will check the headers of the push notification. If it's a sync event, than we make a 'list' request to the GCal API, and then grab it's 'sync' token. We save this token and wait for another push notification. When we get one, we make another list request using our previously saved sync token, which will show us only events that have changed since the last listing. We then replace the sync token we just used with the one we get in our response, get the event that has changed via ID, then create a Discord webhook using the event details to tell us what has changed.
