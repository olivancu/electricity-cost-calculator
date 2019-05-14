from .DR_template import getSignalString
import os.path
import os, sys

from .getSCEEvents import *
from .getPelicanDREvents import *
from .tariff_maps import tariff_maps
from cost_calculator.cost_calculator import *
from openei_tariff.openei_tariff_analyzer import *
from .utils import *
from xbos import get_client

def pollEvents(pollSceApi, sceConfig, pollPelicans, pelicanConfig, mdalClient=None):
    eventStartTimes = []

    if pollSceApi:
        sceStartTimes = pollSCEEvents(sceConfig = sceConfig)
        eventStartTimes = eventStartTimes + sceStartTimes
    if pollPelicans:
        pelicanStartTimes = pollPelicanEvents(pelicanConfig=pelicanConfig, client=mdalClient)
        eventStartTimes = eventStartTimes + pelicanStartTimes
    return eventStartTimes

def checkAndAddNormalDays(eventStartTimes):
    today_day = dtime.datetime.now().date()
    tomorrow_day = today_day + dtime.timedelta(days=1)

    pgeEventDayPresent = False
    sceEventDayPresent = False

    for event in eventStartTimes:
        for eventName in event:
            event_day = convertEpochToUTC(event[eventName]['event_day']).date()
            if event_day == tomorrow_day:
                if eventName == 'PGE_EVENT_SCHEDULED':
                    pgeEventDayPresent = True
                if eventName == 'SCE_EVENT_SCHEDULED' or eventName == 'CPP_COMMERCIAL_SCHEDULED':
                    sceEventDayPresent = True

    if pgeEventDayPresent == False:
        pge_normal_day = {
            'PGE_NORMAL_DAY': {
                'date': float(tomorrow_day.strftime("%s"))
            }
        }
        eventStartTimes.append(pge_normal_day)

    if sceEventDayPresent == False:
        sce_normal_day = {
            'SCE_NORMAL_DAY': {
                'date': float(tomorrow_day.strftime("%s"))
            }
        }
        eventStartTimes.append(sce_normal_day)

    return eventStartTimes



def getHourlyDayPrices(startDateTime, tariff_name='PGEA10', verbose=False, isItEventDay=True):
    eventStartDate = startDateTime.date()

    tariff_openei_data = tariff_maps[tariff_name]
    bill_calc = CostCalculator()
    if isItEventDay:
        pdp_events = list(populate_pdp_events_from_json(openei_tarif_obj=tariff_openei_data, pdp_event_filenames='PDP_events.json'))
        utilityId = int(tariff_openei_data.req_param['eia'])
        # TODO: make more generic
        st = eventStartDate.strftime("%Y-%m-%dT00:00:00-08:00")
        et = eventStartDate.strftime("%Y-%m-%dT23:59:59-08:00")

        if not tariff_openei_data.checkIfPDPDayPresent(utilityId=utilityId, st=st, et=et):
            pdp_events.append({'utility_id': utilityId, 'start_date': st, 'end_date': et})
            update_pdp_json(openei_tarif_obj=tariff_openei_data, pdp_dict=pdp_events, pdp_event_filenames='PDP_events.json')

    if tariff_openei_data.read_from_json() == 0:  # Reading revised JSON blocks containing the utility rates
        if verbose:
            print("Tariff read from JSON successful")
    else:
        print("An error occurred when reading the JSON file" ) # <------------------- handle error
        return

    # TODO: compare start dates of events
    tariff_struct_from_openei_data(tariff_openei_data, bill_calc, pdp_event_filenames='PDP_events.json')

    pd_prices, map_prices = bill_calc.get_electricity_price(timestep=TariffElemPeriod.HOURLY,
                                                            range_date=(dtime.datetime(eventStartDate.year,
                                                                                          eventStartDate.month,
                                                                                          eventStartDate.day, 0, 0, 0).replace(tzinfo=pytz.timezone('US/Pacific')),
                                                                        dtime.datetime(eventStartDate.year,
                                                                                          eventStartDate.month,
                                                                                          eventStartDate.day, 23, 59,
                                                                                          59).replace(tzinfo=pytz.timezone('US/Pacific'))))
    pd_prices = pd_prices.fillna(0)
    energyPrices = pd_prices.customer_energy_charge.values + pd_prices.pdp_non_event_energy_credit.values + pd_prices.pdp_event_energy_charge.values
    demandPrices = pd_prices.customer_demand_charge_season.values + pd_prices.pdp_non_event_demand_credit.values + pd_prices.customer_demand_charge_tou.values

    return {'energyPrices': energyPrices, 'demandPrices': demandPrices}


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


def generateDRSignal(startTime, requestId, eventId, modificationNumber, eventStatus, drEventFilename,
                     signals, group=True, vtnId='LBL-python-VTN', vtnComment='Module', duration='PT1440M',
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

def getMdalClient(pelicanConfig):
    client = None
    if "xbosEntityPath" in list(pelicanConfig.keys()):
        entityPath = pelicanConfig["xbosEntityPath"]
        c = get_client(entity=entityPath)
        client = mdal.MDALClient("xbos/mdal", client=c)
    else:
        c = get_client()
        client = mdal.MDALClient("xbos/mdal", client=c)
    return client


if __name__ == '__main__':
    with open(OADR_PATH+'settings.json') as configFile:
        config = json.load(configFile)

    params = config['params']
    includeDemandPricesFlag = params['includeCurrencyPerKWFlag']
    pollPelicansFlag = params['pollPelicansFlag']
    pollSCEApiFlag = params['pollSCEApiFlag']
    sendToRecipientFlag = params['sendToRecipientFlag']
    recipientURL = params['signal_recipient_url']
    storeEventsFilename = params['eventsHistoryFilename']
    sceTariffs = params['sceTariffs']
    pgeTariffs = params['pgeTariffs']

    sceConfig = None
    if pollSCEApiFlag:
        if 'sce' in list(config.keys()):
            sceConfig = config['sce']

        else:
            print("cannot find sce configuration in settings.json")
            exit(1)

    pelicanConfig = None
    if pollPelicansFlag:
        if 'pelican' in list(config.keys()):
            pelicanConfig = config['pelican']
            mdalClient = getMdalClient(pelicanConfig=pelicanConfig)
        else:
            print("cannot find pelican configuration in settings.json")
            exit(1)

    events = getEventsHistory(eventsFilename=storeEventsFilename)

    eventStartTimes = pollEvents(pollSceApi=pollSCEApiFlag, sceConfig=sceConfig,
                                 pollPelicans=pollPelicansFlag, pelicanConfig=pelicanConfig, mdalClient=mdalClient)
    checkAndAddNormalDays(eventStartTimes)

    for eventInfoDict in eventStartTimes:
        eventName = list(eventInfoDict.keys())[0]
        isItAnEventDay = True
        if eventName.endswith('_SCHEDULED'):

            if eventName.startswith('PGE_EVENT'):
                tariffs = pgeTariffs
            else:
                tariffs = sceTariffs

            event_st_epoch = eventInfoDict[eventName]["start_time"]
            event_et_epoch = eventInfoDict[eventName]["end_time"]
            event_day_st_epoch = eventInfoDict[eventName]["event_day"]
            st = convertEpochToUTC(event_day_st_epoch)

        elif eventName.endswith('_NORMAL_DAY'):
            isItAnEventDay = False
            if eventName.startswith('PGE'):
                tariffs = pgeTariffs
            else:
                tariffs = sceTariffs

            normal_day_st_epoch = eventInfoDict[eventName]["date"]
            st = convertEpochToUTC(normal_day_st_epoch)

        startTime = convertFromDatetimeToString(st)
        # TODO: more flexible
        eventHours = getEventHours(startTime=st, num=24)

        for tariff in tariffs:
            prices = getHourlyDayPrices(startDateTime=st, tariff_name=tariff, isItEventDay=isItAnEventDay)

            if not includeDemandPricesFlag:
                prices = {'energyPrices': prices['energyPrices']}

            signals = []
            for priceSignal in list(prices.keys()):
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

            if isItAnEventDay:
                eventExists = checkIfEventExists(events=events, eventName=eventName, startDate=event_st_epoch, tariff = tariff,
                                                 status=eventStatus)
                if eventExists['prevEventExists']:
                    # TODO: include prices in log file
                    prevPrices = getHourlyDayPrices(startDateTime=st, tariff_name=tariff, isItEventDay=isItAnEventDay)
                    if not includeDemandPricesFlag:
                        prevPrices = {'energyPrices': prevPrices['energyPrices']}

                    if arePricesDifferent(prices1=prices, prices2=prevPrices):
                        # print("LOG------ diff prices", eventName)
                        modificationNumber = eventExists['prevModNumber'] + 1
                        eventId = eventExists['prevEventId']
                    else:
                        # print("LOG------ same prices", eventName)
                        continue

            # print("LOG------ prev event does not exist", eventName)

            # filenames of all the created files
            drSignalFilenames = ""

            # one file for demand prices, one file for energy prices
            for signal in signals:
                drSignalFilename = '%s_%s_%s_%d_%s.xml' % (eventName, tariff, eventId, modificationNumber, signal['signalType'])

                filename, eventId, modificationNumber, startTime = generateDRSignal(
                    startTime=startTime,
                    requestId=requestId,
                    eventId=eventId,
                    modificationNumber=modificationNumber,
                    eventStatus=eventStatus,
                    drEventFilename=drSignalFilename,
                    group=True,
                    groupId=tariff,
                    signals=[signal]
                )

                print(("Event created: %s" % drSignalFilename))
                if sendToRecipientFlag:
                    rsp = sendSignalToServer(url=recipientURL, filename=drSignalFilename)

                if drSignalFilenames == "":
                    drSignalFilenames = drSignalFilename
                else:
                    drSignalFilenames = drSignalFilenames + '_' + drSignalFilename

            newIdx = 0
            if events.empty:
                newIdx = 0
            else:
                newIdx = events.tail(1).index.values[0] + 1

            if isItAnEventDay:
                appendToHistory(idx=newIdx,
                                eventId=eventId,
                                eventName=eventName,
                                modNumber=modificationNumber,
                                startDate=event_st_epoch,
                                status=eventStatus,
                                drSignalFilename=drSignalFilenames,
                                eventsFilename=storeEventsFilename,
                                tariff=tariff)
                events = pandas.read_csv(OADR_PATH+storeEventsFilename, index_col=0)

        # elif eventName.endswith('_ACTIVE'):
        # handle active events
        #     eventStatus = 'active'

        # time.sleep(10)
