import urllib2
import json

'''
url: url to keep polling for SCE events
events: name of SCE DR events to keep polling for (SCHEDULED events)
returns a dictionary: {'eventName': startTimeInEpoch, 'eventName': startTimeInEpoch, ....}
'''


def pollSCEEvents(url, events):
    # events = [unicode(event) for event in events]
    contents = urllib2.urlopen(url).read()
    activeScheduledEvents = json.loads(contents)
    eventStartTimes = {}
    for event in events:
        if unicode(event) in activeScheduledEvents.keys():
            eventStartTimes[event] = activeScheduledEvents[event]
    return eventStartTimes
