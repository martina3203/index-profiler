#!/usr/bin/python

import urllib2
import base64
import logging
import ssl
import xml.etree.ElementTree
import decimal
import argparse
import socket
from operator import itemgetter

#If you want more logging, change the below from logging.INFO to logging.DEBUG
#logging.basicConfig(filename='index-profile-debug.log',level=logging.INFO,mode='w')
#Setting up parser arguments

parser = argparse.ArgumentParser(description='Evaluate the status of the current index slices on the designated device. \
	This script returns a csv output/file that contains a listing on keys with their undying usage of the most recent index slice they exist in. \
	Note that if a key is seldomly used, this may not be from the current slice. This value is displayed as a percentage by default.\
	The first number is the number of sessions currently in this index slice. Think of this as the bookmark for our results.')
parser.add_argument("-f","--OutputFile", help='Designate an output filename that will be a CSV. (indexstatus.csv by default)',default="indexstatus.csv")
parser.add_argument("--host",help='Define the host that we will check the index on. (localhost by default)', default="localhost")
parser.add_argument('--port', help='Define the port that we will attempt to connect on the host. (50105 by default)', default="50105")
parser.add_argument("-S","-s","--SSL", help='Enable this if the REST Port is using SSL. (False by default)', default=False,action="store_true")
parser.add_argument("-u","--username", help='Define the user that will connect on the Service API (admin by default)', default="admin")
parser.add_argument("-p","--password", help='Define the password the user will use to connect to the Service API (netwitness by default)',default="netwitness")
	default=False,action="store_true")
parser.add_argument("-d","-D", help='Debug Mode', default=False,action="store_true")

args = parser.parse_args()
debug = args.d

if debug == True:
	print(args.OutputFile)
	print(args.host)
	print(args.port)
	print(args.S)
	print(args.append)
	print(args.u)
	print(args.p)
	print(args.d)

#These are the default values.
outputfile = args.OutputFile
host=args.host
port=args.port
username=args.u
password=args.p
append=args.append
SSL = args.S
context = ssl._create_unverified_context()
debug = args.d
horizontal = args.horizontal

#This function returns the results of the url commands
def NWRequestURL(host,port,username,password,URLEndString):
	#Encode password as base64
	base64password = base64.b64encode('%s:%s' % (username, password))
	#Build the URL for Request
	if SSL == False:
		URLFullString = "http://" + host + ":" + port + URLEndString
	else:
		URLFullString = "https://" + host + ":" + port + URLEndString

	request = urllib2.Request(URLFullString)
	request.add_header("Authorization", "Basic %s" % base64password)   
	try:
		#logging.debug("Trying URL: " + URLFullString)
		result = urllib2.urlopen(request, context=context)
		#logging.debug("Result Received without HTML Error")
		return result
	except urllib2.HTTPError as e:
		if (e.code == 401):
			print ("401: Unauthorized. May want to check your username/password combination as well as your connection information.")
			exit()
		else:
			print ("Failed! Error code: " + e.code)
			exit()
	except urllib2.URLError as e:
		print("Failed to connect to server:", e.reason)
		print("If you are getting an SSL: UNKNOWN_PROTOCOL Error, your REST API port may not be using SSL like you think it is. Or vice versa.")
		exit()
	except socket.error as e:
		print("Socket Error! Are we sure the service is up and we are connecting on the REST port?")
		exit()

def ParseLanguageResponse(response):
	#Keys as a result of this are formatted like the following:
	#key,description,format,level,valueMax
	languageList = [ ]
	#Skip the first line as it's HTML we don't care about.
	response.next()
	for line in response:
		#Remove new line characters
		strippedline = line.replace("\n","")
		languageList.append(strippedline.split(','))

	#Remove end as we know it's HTML that we don't care about.
	languageList.pop()
	#sort based on key field then return
	languageList = sorted(languageList, key=itemgetter(0))
	return languageList

def ParseSessionsSinceSave(response):
	#Parse XML
	xmltree = xml.etree.ElementTree.parse(response)
	#Grab root of XML
	root = xmltree.getroot()
	#First element should be our winner
	return root[0].text

def ParseIndexInspection(response):
	xmltree = xml.etree.ElementTree.parse(response)
	root = xmltree.getroot()
	indexList = [ ]
	#Find length of xml
	length = len(root[0].findall('params'))

	#For params field, we are going to grab the key as well as the session count for that key
	for index in range(1,length-1):
		#This is our index value
		keyName = root[0][index][0].text
		#This should be our current index session count
		valueCount = root[0][index][2].text
		tempArray = [keyName,valueCount]
		indexList.append(tempArray)

	#sort then return
	indexList = sorted(indexList, key=itemgetter(0))
	return indexList

def Output(language,inspection,sessionCount):
	try:
		if (append == True):
			file = open(outputfile,'a')
		else:
			file = open(outputfile,'w')
	except IOError:
		print("ERROR: Unable to access file. Is it currently open or owned by a different user?")
		return
	#Let's create a dictionary for easy search
	sessionCountDict = { }
	decimal.getcontext().rounding = decimal.ROUND_DOWN
	for item in inspection:
		keyName = item[0]
		countForKey = item[1]
		sessionCountDict[keyName] = countForKey

	#Horizontal print - this includes the individual numbers as well as the percentage.
	if horizontal == True:
		printString = "CURRENT SESSION NUMBER," + sessionCount
		print (printString)
		file.write(printString + "\n")
		printString = "KEY NAME,SESSION COUNT,VALUE MAX,PERCENT USED"
		print (printString)
		file.write(printString + "\n")
		for item in language:
			if item[0] in sessionCountDict:
				percentUsed = 0.0
				#Divde by value count / valueMax to get percent used of the last slice it exists in.
				try:
					percentUsed = float(float(sessionCountDict[item[0]])/float(item[4])*100.0)
					percentUsed = round(percentUsed,1)
				except ZeroDivisionError:
					percentUsed = 0.0
				#Truncate to 2 decimal places
				printString = item[0] + "," +  sessionCountDict[item[0]] + "," + item[4] + "," + str(percentUsed) + "%"
				print (printString)
				file.write(printString + "\n")
			else:
				percentUsed = 0.0
				printString = item[0] + ",0," + item[4] + "," + str(percentUsed) + "%"
				print (printString)
				file.write(printString + "\n")

	else:
		#Create top row with names
		length = len(language)
		if (append == False):	
			printString = "SESSION NUMBER,"
			counter = 0
			for item in language:
				printString = printString + item[0]
				#Add commas except at last item
				if (counter < length-1):
					printString = printString + ","
				counter = counter + 1
			print(printString)
			file.write(printString + "\n")
		#Now, create row of data starting with sessionCount followed by the right percentages
		printString = sessionCount + ","
		counter = 0
		for item in language:
			if item[0] in sessionCountDict:
				try:
					percentUsed = float(float(sessionCountDict[item[0]])/float(item[4])*100.0)
					percentUsed = round(percentUsed,1)
				except ZeroDivisionError:
					percentUsed = 0.0
			else:
				percentUsed = 0.0
			
			printString = printString + str(percentUsed) + "%"
			if (counter < length-1):
				printString = printString + ","
			counter = counter + 1

		print(printString)
		file.write(printString + "\n")

"""
MAIN FUNCTION
"""
#Make Rest Calls
languageResponse=NWRequestURL(host,port,username,password,"/index?msg=language&force-content-type=text/xml")
inspectResponse=NWRequestURL(host,port,username,password,"/index?msg=inspect&force-content-type=text/xml")
sessionsResponse=NWRequestURL(host,port,username,password,"/index/stats/sessions.since.save?msg=get&force-content-type=text/xml")

#Parse the response from Rest Calls
language = ParseLanguageResponse(languageResponse)
sessionCount = ParseSessionsSinceSave(sessionsResponse)
inspection = ParseIndexInspection(inspectResponse)

if debug == True:
	#Debugging the Session Parse
	print("TOTAL SESSION COUNT: ",sessionCount)
	#Debugging the language parse
	print ("LANGUAGE ARRAY:")
	for element in language:
		print("key: " + element[0] + " Description: " + element [1] + " Format: " + element[2] + " Level: " + element[3] + " Value Max: " + element[4])
	#Debugging the inspection parse
	print ("INSPECTION OF CURRENT INDEXES")
	for element in inspection:
		print("key: " + element[0] + " Session Count: " + element[1])

#Write to file
Output(language,inspection,sessionCount)
	