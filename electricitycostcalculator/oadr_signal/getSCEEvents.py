import pandas as pd
# import urllib2
import datetime
from lxml import html
import requests
import pytz

'''
    return [
            {"CPP_COMMERCIAL_SCHEDULED": {
                                            "start_time": 1530939600, 
                                            "end_time": 1530954000, 
                                            "event_day": 1530889200
                                        }
                                    },
            {"CPP_COMMERCIAL_SCHEDULED": {
                                            "start_time": 1530939600, 
                                            "end_time": 1530954000, 
                                            "event_day": 1530889200
                                        }
                                    }]
'''
def pollSCEEvents(sceConfig):
    url = sceConfig['url']
    eventTypes = sceConfig['eventTypesToListenFor']  # CPP

    page = requests.get(url)
    tree = html.fromstring(page.content.replace("\r", "").replace("\t", ""))

    events = []
    for eventType in eventTypes:
        for element in tree.iter():
            if str(element.text).find(eventType) != -1 and str(element.tag) == 'td':
                eventName = eventType+'_COMMERCIAL_SCHEDULED'
                detail_list = [element.text]

                for cpp_detail in element.itersiblings():
                    detail_list.append(cpp_detail.text)

                i = 0
                while i < len(detail_list):
                    if i % 5 == 0:
                        st_date = detail_list[i + 1]
                        et_date = detail_list[i + 2]
                        st_time = detail_list[i + 3]
                        et_time = detail_list[i + 4]

                        event_day = _local_to_utc_epoch(
                            datetime.datetime.strptime("%s %s" % (st_date, "00:00"), "%m/%d/%Y %H:%M"))
                        st = _local_to_utc_epoch(
                            datetime.datetime.strptime("%s %s" % (st_date, st_time), "%m/%d/%Y %I:%M %p"))
                        et = _local_to_utc_epoch(
                            datetime.datetime.strptime("%s %s" % (et_date, et_time), "%m/%d/%Y %I:%M %p"))
                        event = {eventName: {
                            'event_day': float(event_day),
                            'start_time': float(st),
                            'end_time': float(et),
                        }}
                        events.append(event)
                        i += 5

    return events
    # return [{
    #     'CPP_COMMERCIAL_SCHEDULED': {
    #         "start_time": 1536181200,
    #         "end_time": 1536195600,
    #         "event_day": 1536130800
    #     }
    # }]


def _local_to_utc_epoch(timestamp, local_zone="America/Los_Angeles"):
    timestamp_new = pd.to_datetime(timestamp, infer_datetime_format=True, errors='coerce')
    timestamp_new = timestamp_new.tz_localize(local_zone)
    timestamp_new = timestamp_new.strftime('%s')
    return timestamp_new
