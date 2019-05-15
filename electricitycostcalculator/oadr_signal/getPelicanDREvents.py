import datetime
from xbos.services import mdal

def get_uuid_data(UUIDs, freq, names, st, et, client, mdal_functions=mdal.MEAN, aligned=True):
    query1 = {
        "Composition": UUIDs,
        "Selectors": mdal_functions,
       "Time": {
           "T0": st,
           "T1": et,
           "WindowSize": freq,
           "Aligned": aligned,
       },
    }

    resp1 = client.do_query(query1, timeout=300)
    test1 = resp1["df"]
    test1.columns = names
    return test1

'''
    return [
            {"PGE_EVENT_SCHEDULED": {
                                            "start_time": 1530939600, 
                                            "end_time": 1530954000, 
                                            "event_day": 1530889200
                                        }
                                    },
            {"SCE_EVENT_SCHEDULED": {
                                            "start_time": 1530939600, 
                                            "end_time": 1530954000, 
                                            "event_day": 1530889200
                                        }
                                    }]
'''
def pollPelicanEvents(pelicanConfig, client):
    uuid_tariff_map = pelicanConfig['pelican_uuid_tariff_map']
    checkHoursBefore = pelicanConfig['checkHoursBefore']
    events = []
    for tariffName in list(uuid_tariff_map.keys()):
        sensors = list(uuid_tariff_map[tariffName].values())
        names = [col for col in list(uuid_tariff_map[tariffName].keys())]
        mdal_functions = [mdal.MAX for i in range(len(names))]
        freq = '30min'

        dt_now = datetime.datetime.now()
        st = (dt_now - datetime.timedelta(hours=checkHoursBefore)).strftime("%Y-%m-%d %H:%M:%S PDT")
        et = dt_now.strftime("%Y-%m-%d %H:%M:%S PDT")

        df = get_uuid_data(UUIDs=sensors, freq=freq, client=client, names=names, mdal_functions=mdal_functions,
                           st=st, et=et)
        df = df.fillna(0)
        signals = df.fillna(0).loc[(df.start != 0)]
        event = {}
        if signals.start.count() > 0:
            # ASSUMPTION: event starts from 2PM - 6PM

            # converting nanoseconds to seconds (all in UTC)
            epoch = signals.sort_index(ascending=False).tail(1).start.values[0]/1000000000.0
            eventStartTime = datetime.datetime.utcfromtimestamp(epoch)
            eventEndTime = eventStartTime + datetime.timedelta(hours=4)
            eventDayStartTime = eventStartTime - datetime.timedelta(hours=14)

            # TODO: remove the -07:00 time difference (strftime converts to local time)
            event[tariffName+'_EVENT_SCHEDULED'] = {
                'event_day': float(eventDayStartTime.strftime("%s"))-7*3600,
                'start_time': float(eventStartTime.strftime("%s"))-7*3600,
                'end_time': float(eventEndTime.strftime("%s"))-7*3600
            }
            events.append(event)

    return events
    # return [{
    #     'PGE_EVENT_SCHEDULED': {
    #         "start_time": 1536181200,
    #         "end_time": 1536195600,
    #         "event_day": 1536130800
    #     }
    # }]