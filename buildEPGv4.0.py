#!/usr/bin/env python
# -*- coding: utf-8 -*-

##########################################
## buildEPG.py - Builds EPG file for channels present in channels file, taking in account the TV schedule in services.sapo.pt
## Supported channels: http://services.sapo.pt/EPG/GetChannelList
## by warlockPT
## v1.0 - 2015/04/10
##########################################

#imports
import urllib
import datetime
from xml.dom.minidom import parse
from xml.dom.minidom import Document
import xml.dom.minidom
import xml.etree.cElementTree as ET
import os.path

##########################################
## Log flag
# log=0 - No logging
# log=1 - Minimal logging
# log=2 - Full logging
log=1
##########################################

##########################################
## epgFilename - Full filename (including path) for file which will contain EPG
epgFilename="epgFile.xml"
##########################################

##########################################
## channelFilename - Full filename (including path) for file which contains channels
## File format:
##  provCode - Code for which channel is recognized in services.sapo.pt
##  tvg-id - EPG code ID for channel under m3u list
##  name - channel name under m3u list
##  provider - provider where to retrieve the information from
channelFilename="channelList.xml"
##########################################

##########################################
## xmlFilename - Full filename (including path) for file which already contains EPG information
## This is the file that will be used if the defined provider is XML
xmlFilename="guide.xml"
##########################################

allow_xml_provider = None

if (os.path.isfile(xmlFilename)):
    if log>0: print "Opening epg xml file <{0}>...".format(xmlFilename)
    tree = ET.parse(xmlFilename)
    root = tree.getroot()
    allow_xml_provider = True

#get current and next day
today= datetime.datetime.now()
if log>0: print "Start: {0}".format(today)
sDate=str(today.year)+"-"+str(today.month).zfill(2)+"-"+str(today.day).zfill(2)
tomorrow=today+datetime.timedelta(days=8)
eDate=str(tomorrow.year)+"-"+str(tomorrow.month).zfill(2)+"-"+str(tomorrow.day).zfill(2)

if log>0: print "Today: {0}  Tomorrow: {1}".format(sDate, eDate)

url="http://services.sapo.pt/EPG/GetChannelByDateInterval?channelSigla={0}&startDate={1}+00%3A00%3A00&endDate={2}+00%3A00%3A00"

# open epg file
if log>0: print "Opening epgfilename <{0}>...".format(epgFilename)
epgFile = open(epgFilename, 'w')
epgFile.write('<?xml version="1.0" encoding="UTF-8?>\n')
epgFile.write('<tv>\n')

#read channel list
if log>0: print "Opening channel list <{0}>...".format(channelFilename)

DOMTree = xml.dom.minidom.parse(channelFilename)
collection = DOMTree.documentElement
channels = collection.getElementsByTagName("channel")
if log>0: print "Reading channels..."
for channel in channels:
    provCode = channel.getElementsByTagName('provCode')[0]
    tvgIDs = channel.getElementsByTagName('tvg-id')
    provider = channel.getElementsByTagName('provider')[0]

    if provCode.firstChild is None:
        if log>0:
            print "  ProvCode is empty"
        continue

    if tvgIDs.length == 0:
        if log>0:
            print "  No TVGs provided"
        continue

    if provider.firstChild is None:
        if log>0:
            print "  Provider is empty"
        continue

    if allow_xml_provider is not True and provider.firstChild.data == "XML":
        if log>0:
            print "  " + xmlFilename + " not found: XML provider ignored."
        continue

    for tvgID in tvgIDs:

        if tvgID.firstChild is None:
            if log>0:
                print "  TVG is empty"
            continue

        if not tvgID.hasAttributes():
            if log>0:
                print "  TVG doesn't have any attribute"
            continue


        name = tvgID.getAttribute('name')

        if name is None:
            if log>0:
                print "  Provider is empty"
            continue

        if log>0:
            print "  ProvCode: <{0}>  TVG: <{1}>  Name: <{2}> Provider: <{3}>".format(provCode.firstChild.data,tvgID.firstChild.data,name,provider.firstChild.data)

        # add channel info to epgfile
        epgFile.write('\t<channel id="{0}">\n'.format(tvgID.firstChild.data))
        epgFile.write('\t\t<display-name>{0}</display-name>\n'.format(name))
        epgFile.write('\t</channel>\n')

    #format link to web-service
    link = url.format(provCode.firstChild.data, sDate, eDate)
    if log>1: print "    Link: {0}".format(link)

    n=0
    if provider.firstChild.data == 'MEO':
        #read web-service
        f = urllib.urlopen(link)
        myfile = f.read()

        #xml parse
        DOMTree = xml.dom.minidom.parseString(myfile)
        collection = DOMTree.documentElement
        programs = collection.getElementsByTagName("Program")
        if log>0: print "    Reading programs..."
        for program in programs:
            title = program.getElementsByTagName('Title')[0]
            desc = program.getElementsByTagName('Description')[0]
            startTime = program.getElementsByTagName('StartTime')[0]
            endTime = program.getElementsByTagName('EndTime')[0]
            sTime=str(startTime.firstChild.data).translate(None,'-: ')+" +0200" # DST: +0100
            eTime=str(endTime.firstChild.data).translate(None,'-: ')+" +0200" # DST: +0100
            n=n+1
            if log>1:
                print "      Title: ",title.firstChild.data.encode('UTF-8'),"\n    Desc: ",desc.firstChild.data.encode('UTF-8'),"\n    Start: ",startTime.firstChild.data," ",sTime,"\n    End: ",endTime.firstChild.data," ",eTime
                print "      --------------"

            for tvgID in tvgIDs:
                #add program info to epgfile
                epgFile.write('\t<programme channel="{0}" start="{1}" stop="{2}">\n'.format(tvgID.firstChild.data, sTime, eTime))
                epgFile.write('\t\t<title lang="pt">{0}</title>\n'.format(title.firstChild.data.encode( "utf-8" )))
                epgFile.write('\t\t<desc lang="pt">{0}</desc>\n'.format(desc.firstChild.data.encode( "utf-8" )))
                epgFile.write('\t</programme>\n')

    elif provider.firstChild.data == 'XML':
        programs = root.findall("./programme[@channel='"+provCode.firstChild.data+"']")
        for tvgID in tvgIDs:
            for program in programs:
                program.set('start', program.get('start') + " +0200") #.replace('+0100','+0200'))
                program.set('stop', program.get('stop') + " +0200") #.replace('+0100','+0200'))
                if log>1:
                    print "      Title: ",program.find('title').text.encode('UTF-8'),"\n    Desc: ",program.find('desc').text.encode('UTF-8'),"\n    Start: ",program.get('start'),"\n    End: ",program.get('end')
                    print "      --------------"
                program.set('channel', tvgID.firstChild.data)
                epgFile.write("\t" + ET.tostring(program,"utf-8"))
                n=n+1

    if log>0: print "    {0} programs read!".format(n)

#epg xml close
if log>0: print "Closing epgfilename..."
epgFile.write('</tv>\n')
epgFile.close()

today= datetime.datetime.now()
if log>0: print "End: {0}".format(today)
if log>0: print "DONE"
