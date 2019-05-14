import random
import string
import datetime as dtime
import os, sys
sys.path.append(os.path.abspath("../"))  # to access env.py
from env import *

import pandas
import pytz
import requests

def generateAlphanumericId(length=20, createdRandomIds=[]):
    rndm = ''.join(random.choice(string.ascii_lowercase[:6] + string.digits) for _ in range(length))
    if rndm in createdRandomIds:
        return generateAlphanumericId()
    return rndm


def convertFromDatetimeToString(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.00Z')


def getEventHours(startTime, num=24):
    return [convertFromDatetimeToString(startTime + dtime.timedelta(hours=i)) for i in range(num)]


def convertEpochToUTC(epoch):
    return dtime.datetime.utcfromtimestamp(epoch).replace(tzinfo=pytz.utc)



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
        with open(OADR_PATH+eventsFilename, 'w') as f:
            f.write('idx,eventId,eventName,modNumber,eventStartDate,eventStatus,drSignalFilename,tariff\n')
    events = pandas.read_csv(OADR_PATH+eventsFilename, index_col=0)
    return events


def appendToHistory(idx, eventId, eventName, modNumber, startDate, status, drSignalFilename, tariff, eventsFilename='events.csv'):
    with open(OADR_PATH+eventsFilename, 'a') as f:
        f.write('%d,%s,%s,%d,%s,%s,%s,%s\n' % (idx, eventId, eventName, modNumber, startDate, status, drSignalFilename, tariff))


def arePricesDifferent(prices1, prices2):
    keys1 = prices1.keys()
    keys2 = prices2.keys()

    if len(keys1) != len(keys2):
        return True
    elif len(keys1) == 2:
        energyPrices1 = prices1['energyPrices']
        energyPrices2 = prices2['energyPrices']

        demandPrices1 = prices1['demandPrices']
        demandPrices2 = prices2['demandPrices']
        return not (((energyPrices1 == energyPrices2).all()) and ((demandPrices1 == demandPrices2).all()))
    elif len(keys1) == 1:
        if keys1[0] != keys2[0]:
            return True
        else:
            key = keys1[0]
            return not ((prices1[key] == prices2[key]).all())

    # TODO: change default return
    return False

def sendSignalToServer(url, filename):

    # do something
    xml = open(OADR_PATH+"signals/"+filename, "r").read()

    headers = {'Content-Type': 'application/xml'}  # set what your server accepts
    rsp = requests.post(url, data=xml, headers=headers)

    return rsp