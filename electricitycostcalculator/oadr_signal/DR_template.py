def getSignalString(requestId, vtnId, eventId, modificationNumber, createdDateTime, eventStatus, vtnComment,
                    startTime, duration, signals, group, groupId=None, resourceId=None):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml = xml + '<p2012-07:oadrPayload \nxmlns:p2012-07="http://openadr.org/oadr-2.0b/2012/07" \nxmlns:energyinterop="http://docs.oasis-open.org/ns/energyinterop/201110" \nxmlns:icalendar="urn:ietf:params:xml:ns:icalendar-2.0" \nxmlns:icalendar-stream="urn:ietf:params:xml:ns:icalendar-2.0:stream" \nxmlns:payloads="http://docs.oasis-open.org/ns/energyinterop/201110/payloads" \nxmlns:siscale="http://docs.oasis-open.org/ns/emix/2011/06/siscale">\n'
    xml = xml + '\t<p2012-07:oadrSignedObject>\n'
    xml = xml + '\t\t<p2012-07:oadrDistributeEvent>\n'
    xml = xml + '\t\t\t<payloads:requestID>%s</payloads:requestID>\n' % requestId
    xml = xml + '\t\t\t<energyinterop:vtnID>%s</energyinterop:vtnID>\n' % vtnId
    xml = xml + '\t\t\t<p2012-07:oadrEvent>\n'
    xml = xml + '\t\t\t\t<p2012-07:eiEvent>\n'
    xml = xml + '\t\t\t\t\t<energyinterop:eventDescriptor>\n'
    xml = xml + '\t\t\t\t\t\t<energyinterop:eventID>%s</energyinterop:eventID>\n' % eventId
    xml = xml + '\t\t\t\t\t\t<energyinterop:modificationNumber>%d</energyinterop:modificationNumber>\n' % modificationNumber
    xml = xml + '\t\t\t\t\t\t<energyinterop:eiMarketContext />\n'
    xml = xml + '\t\t\t\t\t\t<energyinterop:createdDateTime>%s</energyinterop:createdDateTime>\n' % createdDateTime
    xml = xml + '\t\t\t\t\t\t<energyinterop:eventStatus>%s</energyinterop:eventStatus>\n' % eventStatus
    xml = xml + '\t\t\t\t\t\t<energyinterop:vtnComment>%s</energyinterop:vtnComment>\n' % vtnComment
    xml = xml + '\t\t\t\t\t</energyinterop:eventDescriptor>\n'
    xml = xml + '\t\t\t\t\t<energyinterop:eiActivePeriod>\n'
    xml = xml + '\t\t\t\t\t\t<energyinterop:properties>\n'
    xml = xml + '\t\t\t\t\t\t\t<icalendar:dtstart>\n'
    xml = xml + '\t\t\t\t\t\t\t\t<icalendar:date-time>%s</icalendar:date-time>\n' % startTime
    xml = xml + '\t\t\t\t\t\t\t</icalendar:dtstart>\n'
    xml = xml + '\t\t\t\t\t\t\t<icalendar:duration>\n'
    xml = xml + '\t\t\t\t\t\t\t\t<icalendar:duration>%s</icalendar:duration>\n' % duration
    xml = xml + '\t\t\t\t\t\t\t</icalendar:duration>\n'
    xml = xml + '\t\t\t\t\t\t</energyinterop:properties>\n'
    xml = xml + '\t\t\t\t\t</energyinterop:eiActivePeriod>\n'
    xml = xml + '\t\t\t\t\t<energyinterop:eiEventSignals>\n'

    for signal in signals:
        tagName = 'currencyPerKWh'
        # default signalType = 'energy'
        if signal['signalType'] == 'demand':
            tagName = 'currencyPerKW'

        itemUnits = signal['itemUnits']
        scaleCode = signal['scaleCode']
        eventHours = signal['eventHours']
        prices = signal['prices']
        signalName = signal['signalName']
        signalId = signal['signalId']
        currentPrice = signal['currentPrice']

        xml = xml + '\t\t\t\t\t\t<energyinterop:eiEventSignal>\n'
        xml = xml + '\t\t\t\t\t\t\t<p2012-07:%s>\n' % tagName
        xml = xml + '\t\t\t\t\t\t\t\t<p2012-07:itemDescription>%s</p2012-07:itemDescription>\n' % tagName
        xml = xml + '\t\t\t\t\t\t\t\t<p2012-07:itemUnits>%s</p2012-07:itemUnits>\n' % itemUnits
        xml = xml + '\t\t\t\t\t\t\t\t<siscale:siScaleCode>%s</siscale:siScaleCode>\n' % scaleCode
        xml = xml + '\t\t\t\t\t\t\t</p2012-07:%s>\n' % tagName
        xml = xml + '\t\t\t\t\t\t\t<energyinterop:intervals>\n'
        for i in range(len(eventHours)):
            xml = xml + '\t\t\t\t\t\t\t\t<icalendar-stream:interval>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t<energyinterop:dtstart>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t\t<icalendar:date-time>%s</icalendar:date-time>\n' % (eventHours[i])
            xml = xml + '\t\t\t\t\t\t\t\t\t</energyinterop:dtstart>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t<energyinterop:duration>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t\t<icalendar:duration>PT60M</icalendar:duration>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t</energyinterop:duration>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t<energyinterop:uid>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t\t<icalendar:text>%d</icalendar:text>\n' % (i)
            xml = xml + '\t\t\t\t\t\t\t\t\t</energyinterop:uid>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t<energyinterop:signalPayload>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t\t<energyinterop:payloadFloat>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t\t\t<energyinterop:value>%.2f</energyinterop:value>\n' % (float(prices[i]))
            xml = xml + '\t\t\t\t\t\t\t\t\t\t</energyinterop:payloadFloat>\n'
            xml = xml + '\t\t\t\t\t\t\t\t\t</energyinterop:signalPayload>\n'
            xml = xml + '\t\t\t\t\t\t\t\t</icalendar-stream:interval>\n'
        xml = xml + '\t\t\t\t\t\t\t</energyinterop:intervals>\n'
        xml = xml + '\t\t\t\t\t\t\t<energyinterop:signalName>%s</energyinterop:signalName>\n' % signalName
        xml = xml + '\t\t\t\t\t\t\t<energyinterop:signalType>price</energyinterop:signalType>\n'
        xml = xml + '\t\t\t\t\t\t\t<energyinterop:signalID>%s</energyinterop:signalID>\n' % signalId
        xml = xml + '\t\t\t\t\t\t\t<energyinterop:currentValue>\n'
        xml = xml + '\t\t\t\t\t\t\t\t<energyinterop:payloadFloat>\n'
        xml = xml + '\t\t\t\t\t\t\t\t\t<energyinterop:value>%.2f</energyinterop:value>\n' % currentPrice
        xml = xml + '\t\t\t\t\t\t\t\t</energyinterop:payloadFloat>\n'
        xml = xml + '\t\t\t\t\t\t\t</energyinterop:currentValue>\n'
        xml = xml + '\t\t\t\t\t\t</energyinterop:eiEventSignal>\n'

    xml = xml + '\t\t\t\t\t</energyinterop:eiEventSignals>\n'
    xml = xml + '\t\t\t\t\t<energyinterop:eiTarget>\n'
    if group:
        xml = xml + '\t\t\t\t\t\t<energyinterop:groupID>%s</energyinterop:groupID>\n' % groupId
    else:
        xml = xml + '\t\t\t\t\t\t<energyinterop:resourceID>%s</energyinterop:resourceID>\n' % resourceId
    xml = xml + '\t\t\t\t\t</energyinterop:eiTarget>\n'
    xml = xml + '\t\t\t\t</p2012-07:eiEvent>\n'
    xml = xml + '\t\t\t</p2012-07:oadrEvent>\n'
    xml = xml + '\t\t</p2012-07:oadrDistributeEvent>\n'
    xml = xml + '\t</p2012-07:oadrSignedObject>\n'
    xml = xml + '</p2012-07:oadrPayload>\n'

    return (xml)