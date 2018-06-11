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

    resp1 = client.do_query(query1,timeout=300)
    test1 = resp1["df"]
    test1.columns = names
    return test1

def pollPelicanEvents(pelicanConfig, client):
    uuid_tariff_map = pelicanConfig['pelican_uuid_tariff_map']
    checkHoursBefore = pelicanConfig['checkHoursBefore']
    startTimes = {}
    for tariffName in uuid_tariff_map.keys():
        sensors = uuid_tariff_map[tariffName].values()
        names = [col for col in uuid_tariff_map[tariffName].keys()]
        mdal_functions = [mdal.MAX for i in range(len(names))]
        freq = '30min'

        dt_now = datetime.datetime.now()
        st = (dt_now - datetime.timedelta(hours=checkHoursBefore)).strftime("%Y-%m-%d %H:%M:%S PST")
        et = dt_now.strftime("%Y-%m-%d %H:%M:%S PST")

        df = get_uuid_data(UUIDs=sensors, freq=freq, client=client, names=names, mdal_functions=mdal_functions,
                           st=st, et=et)
        df = df.fillna(0)
        signals = df.fillna(0).loc[(df.type != 0) | (df.status == 3)]
        if signals.status.count() > 0:
            startTimes[tariffName[:3] + '_EVENT_SCHEDULED'] = signals.sort_index(ascending=False).tail(1).start.values[0]

    return startTimes