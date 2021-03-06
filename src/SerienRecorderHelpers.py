﻿# coding=utf-8

# This file contain some helper functions
# which called from other SerienRecorder modules
import base64

from Components.config import config
from Components.AVSwitch import AVSwitch

from enigma import eServiceReference, eTimer, eServiceCenter, eEPGCache, ePicLoad, iServiceInformation

from Screens.ChannelSelection import service_types_tv
from ServiceReference import ServiceReference

from Tools.Directories import fileExists

import datetime, os, re, urllib2, sys, time

# ----------------------------------------------------------------------------------------------------------------------
#
# Common functions
#
# ----------------------------------------------------------------------------------------------------------------------

# Useragent
WebTimeout = 10

STBTYPE = None
SRVERSION = '3.8.0'

def writeTestLog(text):
	if not fileExists("/usr/lib/enigma2/python/Plugins/Extensions/serienrecorder/TestLogs"):
		open("/usr/lib/enigma2/python/Plugins/Extensions/serienrecorder/TestLogs", 'w').close()

	writeLogFile = open("/usr/lib/enigma2/python/Plugins/Extensions/serienrecorder/TestLogs", "a")
	writeLogFile.write('%s\n' % text)
	writeLogFile.close()

def decodeISO8859_1(txt, replace=False):
	txt = unicode(txt, 'ISO-8859-1')
	txt = txt.encode('utf-8')
	if replace:
		txt = doReplaces(txt)
	return txt

def doReplaces(txt):
	non_allowed_characters = "/.\\:*?<>|\"'"
	cleanedString = ''

	for c in txt:
		if c in non_allowed_characters or ord(c) < 32:
			c = "_"
		cleanedString += c

	cleanedString = cleanedString.replace('&amp;','&').replace('&apos;',"'").replace('&gt;','>').replace('&lt;','<').replace('&quot;','"')
	cleanedString = re.sub(r"\[.*\]", "", cleanedString).strip()
	return cleanedString

def getSeriesIDByURL(url):
	result = None
	if url:
		seriesID = re.findall('epg_print.pl\?s=([0-9]+)', url)
		if seriesID:
			result = seriesID[0]
	return result

def isDreamOS():
	try:
		from enigma import eMediaDatabase
	except ImportError:
		isDreamboxOS = False
	else:
		isDreamboxOS = True
	return isDreamboxOS

def checkCI(servref = None, cinum = 0):
	cifile = "/etc/enigma2/ci%d.xml" % cinum

	if servref is None or not os.path.exists(cifile):
		return -1

	serviceref = servref.toString()
	serviceHandler = eServiceCenter.getInstance()
	info = serviceHandler.info(servref)
	provider = "unknown"
	if info is not None:
		provider = info.getInfoString(servref, iServiceInformation.sProvider)

	sp = serviceref.split(":")
	namespace = ""
	if len(sp) > 6:
		namespace = sp[6]

	f = open(cifile, "r")
	assignments = f.read()
	f.close()
	if assignments.find(serviceref) is not -1:
		# print "[AUTOPIN] CI Slot %d assigned to %s" % (cinum+1, serviceref)
		return cinum
	if assignments.find("provider name") is -1:
		return -1
	# service not found, but maybe provider ...
	providerstr = "provider name=\"%s\" dvbnamespace=\"%s\"" % (provider, namespace)
	if assignments.find(providerstr) is not -1:
		# print "[AUTOPIN] CI Slot %d assigned to %s via provider %s" % (cinum+1, serviceref, provider)
		return cinum

	return -1

def encrypt(key, clear):
	enc = []
	for i in range(len(clear)):
		key_c = key[i % len(key)]
		enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
		enc.append(enc_c)
	return base64.urlsafe_b64encode("".join(enc))

def decrypt(key, enc):
	dec = []
	enc = base64.urlsafe_b64decode(enc)
	for i in range(len(enc)):
		key_c = key[i % len(key)]
		dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
		dec.append(dec_c)
	return "".join(dec)

def getmac(interface):
	try:
		mac = open('/sys/class/net/'+interface+'/address').readline()
	except:
		mac = "00:00:00:00:00:00"
	return mac[0:17]

def getChangedSeriesNames(markers):
	IDs = []
	for marker in markers:
		(Serie, WLID) = marker
		IDs.append(WLID)

	from SerienRecorderSeriesServer import SeriesServer
	series = SeriesServer().getSeriesNamesAndWLID(IDs)

	result = {}
	for marker in markers:
		try:
			(Serie, WLID) = marker
			if Serie != series[str(WLID)]:
				result[str(WLID)] = (Serie, series[str(WLID)])
		except:
			continue
	return result


# ----------------------------------------------------------------------------------------------------------------------
#
# TimeHelper - Time related helper functions
# All methods are "static" and the TimeHelper class is more or less a namespace only
#
# Use: TimeHelpers::getNextDayUnixtime(...)
#
# ----------------------------------------------------------------------------------------------------------------------

class TimeHelpers:
	def __init__(self):
		pass

	@classmethod
	def getNextDayUnixtime(cls, minutes, hour, day, month):
		now = datetime.datetime.now()
		if int(month) < now.month:
			date = datetime.datetime(int(now.year) + 1,int(month),int(day),int(hour),int(minutes))
		else:
			date = datetime.datetime(int(now.year),int(month),int(day),int(hour),int(minutes))
		date += datetime.timedelta(days=1)
		return date.strftime("%s")

	@classmethod
	def getUnixTimeAll(cls, minutes, hour, day, month):
		now = datetime.datetime.now()
		if int(month) < now.month:
			return datetime.datetime(int(now.year) + 1, int(month), int(day), int(hour), int(minutes)).strftime("%s")
		else:
			return datetime.datetime(int(now.year), int(month), int(day), int(hour), int(minutes)).strftime("%s")

	@classmethod
	def getUnixTimeWithDayOffset(cls, hour, minutes, AddDays):
		now = datetime.datetime.now()
		date = datetime.datetime(now.year, now.month, now.day, int(hour), int(minutes))
		date += datetime.timedelta(days=AddDays)
		return date.strftime("%s")

	@classmethod
	def getRealUnixTime(cls, minutes, hour, day, month, year):
		return datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes)).strftime("%s")

	@classmethod
	def getRealUnixTimeWithDayOffset(cls, minutes, hour, day, month, year, AddDays):
		date = datetime.datetime(int(year), int(month), int(day), int(hour), int(minutes))
		date += datetime.timedelta(days=AddDays)
		return date.strftime("%s")
		
	@classmethod
	def allowedTimeRange(cls, fromTime, toTime, start_time, end_time):
		if fromTime < toTime:
			if start_time < end_time:
				if (start_time >= fromTime) and (end_time <= toTime):
					return True
		else:
			if start_time >= fromTime:
				if end_time >= fromTime:
					if start_time < end_time:
						return True
				elif end_time <= toTime:
					return True
			elif start_time < end_time:
				if (start_time <= toTime) and (end_time <= toTime):
					return True
		return False

	@classmethod
	def td2HHMMstr(cls, td):
		# Convert timedelta objects to a HH:MM string with (+/-) sign
		if td < datetime.timedelta(seconds=0):
			sign='-'
			td = -td
		else:
			sign = ''

		if sys.version_info < (2, 7):
			def tts(timedelta):
				return (timedelta.microseconds + 0.0 + (timedelta.seconds + timedelta.days * 24 * 3600) * 10 ** 6) / 10 ** 6
			tdstr_s = '{0}{1:}:{2:02d}'
		else:
			def tts(timedelta):
				return timedelta.total_seconds()
			tdstr_s = '{}{:}:{:02d}'

		tdhours, rem = divmod(tts(td), 3600)
		tdminutes, rem = divmod(rem, 60)
		tdstr = tdstr_s.format(sign, int(tdhours), int(tdminutes))
		return tdstr

	@classmethod
	def getMailSearchString(cls):
		date = datetime.date.today() - datetime.timedelta(config.plugins.serienRec.imap_mail_age.value)
		months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
		searchstr = '(SENTSINCE {day:02d}-{month}-{year:04d} SUBJECT "' + config.plugins.serienRec.imap_mail_subject.value + '")'
		searchstr = searchstr.format(day=date.day, month=months[date.month - 1], year=date.year)
		return searchstr


# ----------------------------------------------------------------------------------------------------------------------
#
# STBHelpers - STB related helper functions
# All methods are "static" and the STBHelper class is more or less a namespace only
#
# Use: STBHelpers::getServiceList(...)
#
# ----------------------------------------------------------------------------------------------------------------------

class STBHelpers:

	def __init__(self):
		pass

	@classmethod
	def getServiceList(cls, ref):
		root = eServiceReference(str(ref))
		serviceHandler = eServiceCenter.getInstance()
		return serviceHandler.list(root).getContent("SN", True)

	@classmethod
	def getTVBouquets(cls):
		return cls.getServiceList(service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet')

	@classmethod
	def buildSTBChannelList(cls, BouquetName=None):
		serien_chlist = []
		mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
		print "[SerienRecorder] read STB Channellist.."
		tvbouquets = cls.getTVBouquets()
		print "[SerienRecorder] found %s bouquet: %s" % (len(tvbouquets), tvbouquets)

		if not BouquetName:
			for bouquet in tvbouquets:
				bouquetlist = cls.getServiceList(bouquet[0])
				for (serviceref, servicename) in bouquetlist:
					playable = not (eServiceReference(serviceref).flags & mask)
					if playable:
						serien_chlist.append((servicename, serviceref))
		else:
			for bouquet in tvbouquets:
				if bouquet[1] == BouquetName:
					bouquetlist = cls.getServiceList(bouquet[0])
					for (serviceref, servicename) in bouquetlist:
						playable = not (eServiceReference(serviceref).flags & mask)
						if playable:
							serien_chlist.append((servicename, serviceref))
					break
		return serien_chlist

	@classmethod
	def getChannelByRef(cls, stb_chlist,serviceref):
		for (channelname,channelref) in stb_chlist:
			if channelref == serviceref:
				return channelname

	@classmethod
	def getEPGTimeSpan(cls):
		return int(config.plugins.serienRec.epgTimeSpan.value)

	@classmethod
	def getEPGEvent(cls, query, channelref, title, starttime):
		if not query or len(query) != 2:
			return

		epgmatches = []
		epgcache = eEPGCache.getInstance()
		allevents = epgcache.lookupEvent(query) or []

		for serviceref, eit, name, begin, duration, shortdesc, extdesc in allevents:
			_name = name.strip().replace(".","").replace(":","").replace("-","").replace("  "," ").lower()
			_title = title.strip().replace(".","").replace(":","").replace("-","").replace("  "," ").lower()

			lowEPGStartTime = int(int(begin) - (int(cls.getEPGTimeSpan()) * 60))
			highEPGStartTime = int(int(begin) + (int(cls.getEPGTimeSpan()) * 60))
			if (channelref == serviceref) and (_name.count(_title) or _title.count(_name)):
				if bool(lowEPGStartTime <= int(starttime) <= highEPGStartTime):
					epgmatches.append((serviceref, eit, name, begin, duration, shortdesc, extdesc))
					break
		return epgmatches

	@classmethod
	def getStartEndTimeFromEPG(cls, start_unixtime_eit, end_unixtime_eit, margin_before, margin_after, serien_name, STBRef):
		eit = 0
		if config.plugins.serienRec.eventid.value:
			# event_matches = self.getEPGevent(['RITBDSE',("1:0:19:EF75:3F9:1:C00000:0:0:0:", 0, 1392755700, -1)], "1:0:19:EF75:3F9:1:C00000:0:0:0:", "2 Broke Girls", 1392755700)
			event_matches = cls.getEPGEvent(['RITBDSE', (STBRef, 0, int(start_unixtime_eit) + (int(margin_before) * 60), -1)], STBRef, serien_name, int(start_unixtime_eit) + (int(margin_before) * 60))
			if event_matches and len(event_matches) > 0:
				for event_entry in event_matches:
					print "[SerienRecorder] found eventID: %s" % int(event_entry[1])
					eit = int(event_entry[1])
					start_unixtime_eit = int(event_entry[3]) - (int(margin_before) * 60)
					end_unixtime_eit = int(event_entry[3]) + int(event_entry[4]) + (int(margin_after) * 60)
					break

		return eit, end_unixtime_eit, start_unixtime_eit

	@classmethod
	def countEpisodeOnHDD(cls, dirname, seasonEpisodeString, serien_name, stopAfterFirstHit = False, title = None):
		count = 0
		if fileExists(dirname):
			if title is None:
				searchString = '%s.*?%s.*?\.(ts|mkv|avi|mp4|divx|xvid|mpg|mov)\Z' % (re.escape(serien_name), re.escape(seasonEpisodeString))
			else:
				searchString = '%s.*?%s.*?%s.*?\.(ts|mkv|avi|mp4|divx|xvid|mpg|mov)\Z' % (re.escape(serien_name), re.escape(seasonEpisodeString), re.escape(title))
			dirs = os.listdir(dirname)
			for dir in dirs:
				if re.search(searchString, dir):
					count += 1
					if stopAfterFirstHit:
						break

		return count

	@classmethod
	def getImageVersionString(cls):
		from Components.About import about

		creator = "n/a"
		version = "n/a"

		if hasattr(about,'getVTiVersionString'):
			creator = about.getVTiVersionString()
		else:
			creator = about.getEnigmaVersionString()
		version = about.getVersionString()

		return ' / '.join((creator, version))

	@classmethod
	def getSTBType(cls):
		try:
			from Tools.HardwareInfoVu import HardwareInfoVu
			STBType = HardwareInfoVu().get_device_name()
		except:
			try:
				from Tools.HardwareInfo import HardwareInfo
				STBType = HardwareInfo().get_device_name()
			except:
				STBType = "unknown"
		return STBType

	@classmethod
	def getHardwareUUID(cls):
		try:
			file = open("/var/lib/dbus/machine-id", "r")
			uuid = file.readline().strip()
			file.close()
		except:
			uuid = "unknown"
		return uuid

# ----------------------------------------------------------------------------------------------------------------------
#
# PicLoader
#
# ----------------------------------------------------------------------------------------------------------------------

class PicLoader:
	def __init__(self, width, height, sc=None):
		self.picload = ePicLoad()
		if not sc:
			sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((width, height, sc[0], sc[1], False, 1, "#ff000000"))

	def load(self, filename):
		if isDreamOS():
			self.picload.startDecode(filename, False)
		else:
			self.picload.startDecode(filename, 0, 0, False)
		data = self.picload.getData()
		return data

	def destroy(self):
		del self.picload

# ----------------------------------------------------------------------------------------------------------------------
#
# imdbVideo
#
# ----------------------------------------------------------------------------------------------------------------------

class imdbVideo():
	def __init__(self):
		print "imdbvideos.."

	@staticmethod
	def videolist(url):
		url += "videogallery"
		print url
		headers = { 'User-Agent' : 'Mozilla/5.0' }
		req = urllib2.Request(url, None, headers)
		data = urllib2.urlopen(req).read()
		lst = []
		videos = re.findall('viconst="(.*?)".*?src="(.*?)" class="video" />', data, re.S)
		if videos:
			for id,image in videos:
				url = "http://www.imdb.com/video/screenplay/%s/imdb/single" % id
				lst.append((url, image))

		if len(lst) != 0:
			return lst
		else:
			return None

	@staticmethod
	def stream_url(url):
		headers = { 'User-Agent' : 'Mozilla/5.0' }
		req = urllib2.Request(url, None, headers)
		data = urllib2.urlopen(req).read()
		stream_url = re.findall('"start":0,"url":"(.*?)"', data, re.S)
		if stream_url:
			return stream_url[0]
		else:
			return None

	@staticmethod
	def dataError(error):
		return None

# ----------------------------------------------------------------------------------------------------------------------
#
# Picon loader
#
# ----------------------------------------------------------------------------------------------------------------------

class PiconLoader:
	def __init__(self):
		self.nameCache = { }
		self.partnerbox = re.compile('1:0:[0-9a-fA-F]+:[1-9a-fA-F]+[0-9a-fA-F]*:[1-9a-fA-F]+[0-9a-fA-F]*:[1-9a-fA-F]+[0-9a-fA-F]*:[1-9a-fA-F]+[0-9a-fA-F]*:[0-9a-fA-F]+:[0-9a-fA-F]+:[0-9a-fA-F]+:http')

	def getPicon(self, sRef):
		if not sRef:
			return None

		pos = sRef.rfind(':')
		pos2 = sRef.rfind(':', 0, pos)
		if pos - pos2 == 1 or self.partnerbox.match(sRef) is not None:
			sRef = sRef[:pos2].replace(':', '_')
		else:
			sRef = sRef[:pos].replace(':', '_')
		pngname = self.nameCache.get(sRef, "")
		if pngname == "":
			pngname = self.findPicon(sRef)
			if pngname != "":
				self.nameCache[sRef] = pngname
			if pngname == "": # no picon for service found
				pngname = self.nameCache.get("default", "")
				if pngname == "": # no default yet in cache..
					pngname = self.findPicon("picon_default")
					if pngname != "":
						self.nameCache["default"] = pngname
		if fileExists(pngname):
			return pngname
		else:
			return None

	@staticmethod
	def findPicon(sRef):
		pngname = "%s%s.png" % (config.plugins.serienRec.piconPath.value, sRef)
		if not fileExists(pngname):
			pngname = ""
		return pngname

	def piconPathChanged(self, configElement = None):
		self.nameCache.clear()


