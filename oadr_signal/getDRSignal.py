import datetime as dtime
import random
import string
from DR_template import getSignalString
import pandas
import os.path

from oadr_signal.getSCEEvents import *
from tariff_maps import tariff_maps
from cost_calculator.cost_calculator import *
from openei_tariff.openei_tariff_analyzer import *
from env import *

def pollEvents(sceUrl, sceEvents, pgeURIs):
    eventStartTimes = pollSCEEvents(url=sceUrl, events=sceEvents)

    #TODO: get event start times from PG&E events too

    return eventStartTimes

def generateAlphanumericId(length=20, createdRandomIds=[]):
    rndm = ''.join(random.choice(string.ascii_lowercase[:6] + string.digits) for _ in range(length))
    if rndm in createdRandomIds:
        return generateAlphanumericId()
    return rndm

def getHourlyEventDayPrices(startDateTime, tariff_name='PGEA10', verbose=False):
    eventStartDate = startDateTime.date()

    tariff_openei_data = tariff_maps[tariff_name]
    bill_calc = CostCalculator()
    pdp_events = list(populate_pdp_events_from_json(openei_tarif_obj=tariff_openei_data, pdp_event_filenames='PDP_events.json'))
    utilityId = int(tariff_openei_data.req_param['eia'])
    # TODO: make more generic
    st = eventStartDate.strftime("%Y-%m-%dT14:00:00-08:00")
    et = eventStartDate.strftime("%Y-%m-%dT18:00:00-08:00")

    if not tariff_openei_data.checkIfPDPDayPresent(utilityId=utilityId, st=st, et=et):
        pdp_events.append({'utility_id': utilityId, 'start_date': st, 'end_date': et})
        update_pdp_json(openei_tarif_obj=tariff_openei_data, pdp_dict=pdp_events, pdp_event_filenames='PDP_events.json')

    if tariff_openei_data.read_from_json() == 0:  # Reading revised JSON blocks containing the utility rates
        if verbose:
            print ("Tariff read from JSON successful")
    else:
        print("An error occurred when reading the JSON file" ) # <------------------- handle error
        return

    # TODO: compare start dates of events
    tariff_struct_from_openei_data(tariff_openei_data, bill_calc, pdp_event_filenames='PDP_events.json')

    pd_prices, map_prices = bill_calc.get_electricity_price(timestep=TariffElemPeriod.HOURLY,
                                                            range_date=(dtime.datetime(eventStartDate.year,
                                                                                          eventStartDate.month,
                                                                                          eventStartDate.day, 0, 0, 0),
                                                                        dtime.datetime(eventStartDate.year,
                                                                                          eventStartDate.month,
                                                                                          eventStartDate.day, 23, 59,
                                                                                          59)))
    pd_prices = pd_prices.fillna(0)
    energyPrices = pd_prices.customer_energy_charge.values + pd_prices.pdp_non_event_energy_credit.values + pd_prices.pdp_event_energy_charge.values
    demandPrices = pd_prices.customer_demand_charge_season.values + pd_prices.pdp_non_event_demand_credit.values + pd_prices.customer_demand_charge_tou.values

    return {'energyPrices': energyPrices, 'demandPrices': demandPrices}


def convertFromDatetimeToString(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.00Z')


def getEventHours(startTime, num=24):
    return [convertFromDatetimeToString(startTime + dtime.timedelta(hours=i)) for i in range(num)]


def convertEpochToUTC(epoch):
    return dtime.datetime.utcfromtimestamp(epoch).replace(tzinfo=pytz.utc)

def createPriceSignal(eventHours, prices, signalId, itemUnits='USD', scaleCode='none',
                      isEnergySignal=True, signalName='ENERGY_PRICE', currentPrice=0):
    signal = {}
    if isEnergySignal:
        signal['signalType'] = 'energy'
    else:
        signal['signalType'] = 'demand'
    signal['itemUnits'] = itemUnits
    signal['scaleCode'] = scaleCode
    signal['eventHours'] = eventHours
    signal['prices'] = prices
    signal['signalName'] = signalName
    signal['signalId'] = signalId
    signal['currentPrice'] = currentPrice

    return signal


def generateDRSignal(event, startTime, prices, requestId, eventId, modificationNumber, eventStatus, drEventFilename,
                     signals, group=True, vtnId='SCE-python-VTN-LBL', vtnComment='Module', duration='PT1440M',
                     groupId='PGEA10', resourceId='csu-dominguez'):
    createdDateTime = convertFromDatetimeToString(dtime.datetime.utcnow())
    xml = getSignalString(requestId=requestId,
                          vtnId=vtnId,
                          eventId=eventId,
                          modificationNumber=modificationNumber,
                          createdDateTime=createdDateTime,
                          eventStatus=eventStatus,
                          vtnComment=vtnComment,
                          startTime=startTime,
                          duration=duration,
                          signals=signals,
                          group=group,
                          groupId=groupId,
                          resourceId=resourceId)

    if not os.path.isdir(OADR_PATH+'signals'):
        os.makedirs(OADR_PATH+'signals')

    with open(OADR_PATH+'signals/'+drEventFilename, "w") as f:
        f.write(xml)
    return drEventFilename, eventId, modificationNumber, startTime


def sendSignalToServer(filename):
    # do something
    return


def checkIfEventExists(events, startDate, eventName, tariff, status=None):
    # handle different eventStatuses <----------------- do this
    if events.loc[(events.eventName == eventName) & (events.eventStartDate == startDate) & (events.tariff == tariff)].eventStartDate.count() > 0:
        e = events.loc[(events.eventName == eventName) & (events.eventStartDate == startDate) & (events.tariff == tariff)].tail(1)
        prevModNumber = e.modNumber.values[0]
        prevEventId = e.eventId.values[0]
        return {'prevEventExists': True, 'prevEventId': prevEventId, 'prevModNumber': prevModNumber}
    else:
        return {'prevEventExists': False}


def getEventsHistory(eventsFilename='events.csv'):
    path = OADR_PATH + eventsFilename
    if os.path.exists(path) == False:
        with open(eventsFilename, 'w') as f:
            f.write('idx,eventId,eventName,modNumber,eventStartDate,eventStatus,drSignalFilename,tariff\n')
    events = pandas.read_csv(eventsFilename, index_col=0)
    return events


def appendToHistory(idx, eventId, eventName, modNumber, startDate, status, drSignalFilename, tariff, eventsFilename='events.csv'):
    with open(eventsFilename, 'a') as f:
        f.write('%d,%s,%s,%d,%s,%s,%s,%s\n' % (idx, eventId, eventName, modNumber, startDate, status, drSignalFilename, tariff))


def arePricesDifferent(prices1, prices2):
    keys1 = prices1.keys()
    keys2 = prices2.keys()

    if len(keys1) != len(keys2):
        return True

    energyPrices1 = prices1['energyPrices']
    energyPrices2 = prices2['energyPrices']

    demandPrices1 = prices1['demandPrices']
    demandPrices2 = prices2['demandPrices']
    # print("LOG----- prices different: ",~(((energyPrices1 == energyPrices2).all()) & ((demandPrices1 == demandPrices2).all())))
    return not (((energyPrices1 == energyPrices2).all()) & ((demandPrices1 == demandPrices2).all()))


if __name__ == '__main__':
    with open('settings.json') as configFile:
        config = json.load(configFile)

    sce_config = config['sce']
    url = sce_config['url']
    eventsToListenFor = sce_config['eventsToListenFor']
    storeEventsFilename = sce_config['eventsHistoryFilename']
    tariffs = sce_config['tariffs']

    events = getEventsHistory(eventsFilename=storeEventsFilename)
    # print("LOG--------- main")
    while True:
        eventStartTimes = pollEvents(sceUrl=url, sceEvents=eventsToListenFor, pgeURIs=None)

        if eventStartTimes != {}:
            # print("LOG--------- not null events ")
            for eventName in eventStartTimes.keys():
                if eventName.endswith('_SCHEDULED'):
                    st_epoch = eventStartTimes[eventName]
                    st = convertEpochToUTC(st_epoch / 1000.0)
                    startTime = convertFromDatetimeToString(st)
                    # TODO: more flexible
                    eventHours = getEventHours(startTime=st, num=24)

                    for tariff in tariffs:
                        prices = getHourlyEventDayPrices(startDateTime=st, tariff_name=tariff)
                        signals = []
                        for priceSignal in prices.keys():
                            # print("LOG--------- price key: ",priceSignal, eventName)
                            signalId = generateAlphanumericId()
                            signal = {}
                            if priceSignal == 'demandPrices':
                                signal = createPriceSignal(eventHours=eventHours, prices=prices['demandPrices'],
                                                           isEnergySignal=False, signalId=signalId,
                                                           signalName='DEMAND_PRICE', currentPrice=0);
                            else:
                                signal = createPriceSignal(eventHours=eventHours, prices=prices['energyPrices'],
                                                           isEnergySignal=True, signalId=signalId,
                                                           signalName='ENERGY_PRICE', currentPrice=0);
                            signals.append(signal)

                        eventId = generateAlphanumericId()
                        modificationNumber = 0
                        eventStatus = 'far'
                        requestId = generateAlphanumericId()

                        eventExists = checkIfEventExists(events=events, eventName=eventName, startDate=st_epoch, tariff = tariff,
                                                         status=eventStatus)
                        if eventExists['prevEventExists']:
                            # print("LOG------ prev event exists", eventName)
                            prevPrices = getHourlyEventDayPrices(startDateTime=st, tariff_name=tariff)  # change this <---------- include prices in the file
                            if arePricesDifferent(prices1=prices, prices2=prevPrices):
                                # print("LOG------ diff prices", eventName)
                                modificationNumber = eventExists['prevModNumber'] + 1
                                eventId = eventExists['prevEventId']
                            else:
                                # print("LOG------ same prices", eventName)
                                continue

                        # print("LOG------ prev event does not exist", eventName)
                        drSignalFilename = '%s_%s_%s_%d.xml' % (eventName, tariff, eventId, modificationNumber)

                        filename, eventId, modificationNumber, startTime = generateDRSignal(
                            event=eventName,
                            startTime=startTime,
                            prices=prices,
                            requestId=requestId,
                            eventId=eventId,
                            modificationNumber=modificationNumber,
                            eventStatus=eventStatus,
                            drEventFilename=drSignalFilename,
                            group=True,
                            groupId=tariff,
                            signals=signals
                        )

                        newIdx = 0
                        if events.empty:
                            newIdx = 0
                        else:
                            newIdx = events.tail(1).index.values[0] + 1

                        appendToHistory(idx=newIdx,
                                        eventId=eventId,
                                        eventName=eventName,
                                        modNumber=modificationNumber,
                                        startDate=st_epoch,
                                        status=eventStatus,
                                        drSignalFilename=drSignalFilename,
                                        eventsFilename='events.csv',
                                        tariff=tariff)
                        events = pandas.read_csv(OADR_PATH+storeEventsFilename, index_col=0)
                        print("Event created: %s"%drSignalFilename)
                        sendSignalToServer(filename=drSignalFilename)

            # elif eventName.endswith('_ACTIVE'):
            # handle active events
            #     eventStatus = 'active'
        time.sleep(10)