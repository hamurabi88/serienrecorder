# coding=utf-8

# This file contains the SerienRecoder Serien Server stuff

from SerienRecorderHelpers import *


# Constants
SERIES_SERVER_URL = 'http://www.serienserver.de/cache/cache.php'
REQUEST_PARAMETER = "?device=" + STBHelpers.getSTBType() + "&version=SR" + SRVERSION + "&uuid=" + STBHelpers.getHardwareUUID()

try:
	import xmlrpclib
except ImportError as ie:
	xmlrpclib = None

class TimeoutTransport (xmlrpclib.Transport):
	"""
	Custom XML-RPC transport class for HTTP connections, allowing a timeout in
	the base connection.
	"""
	def __init__(self, timeout=10, use_datetime=0):
		xmlrpclib.Transport.__init__(self, use_datetime)
		self._timeout = timeout

	def make_connection(self, host):
		import httplib
		import ssl
		host, extra_headers, x509 = self.get_host_info(host)
		if hasattr(ssl, '_create_unverified_context'):
			ssl._create_default_https_context = ssl._create_unverified_context
		return httplib.HTTPSConnection(host, timeout=self._timeout)

class SeriesServer:

	def __init__(self):
		# Check dependencies
		if xmlrpclib is not None:
			t = TimeoutTransport(7)
			self.server = xmlrpclib.ServerProxy(SERIES_SERVER_URL + REQUEST_PARAMETER, transport=t)

	def getSeriesID(self, seriesName):
		try:
			return self.server.sp.cache.getID(seriesName)
		except:
			return 0

	def getIDByFSID(self, fsID):
		try:
			return self.server.sp.cache.getIDByFSID(fsID)
		except:
			return 0

	def getSeriesNamesAndWLID(self, wlIDs):
		try:
			return self.server.sp.cache.getNamesByWLIDs(wlIDs)
		except:
			return {}

	def getSeriesInfo(self, seriesID):
		infoText = ""
		try:
			seriesInfo = self.server.sp.cache.getSeriesInfo(seriesID)
		except:
			return infoText
		# Title
		if 'title' in seriesInfo:
			infoText += seriesInfo['title'].encode('utf-8')

		# Year
		if 'year' in seriesInfo:
			infoText += " (%s)" % seriesInfo['year']

		# Info
		if 'info' in seriesInfo:
			infoText += "\n%s" % seriesInfo['info']

		# Fan count
		if 'fancount' in seriesInfo:
			infoText += ("\n\nDie Serie hat %s Fans" % seriesInfo['fancount'])

		# Rating
		if 'rating' in seriesInfo:
			infoText += (" und eine Bewertung von %.1f" % float(seriesInfo['rating']))

		# Sex
		if 'male' in seriesInfo and 'female' in seriesInfo and 'age' in seriesInfo:
			infoText += ("\nZielgruppe: %s (Männer: %s, Frauen: %s)" % (seriesInfo['age'], seriesInfo['male'], seriesInfo['female']))

		# Transmission info
		infoText += "\n\n"
		if 'seasons_and_episodes' in seriesInfo:
			infoText += "%s\n" % seriesInfo['seasons_and_episodes'].encode('utf-8')

		if 'transmissioninfo' in seriesInfo:
			infoText += "%s\n" % seriesInfo['transmissioninfo']

		infoText += "\n"
		# Description
		if 'description' in seriesInfo:
			infoText += seriesInfo['description'].encode('utf-8')

		# Upfronts
		if 'upfronts' in seriesInfo:
			infoText += "\n\n"
			glue = '\n'
			infoText += "%s\n" % glue.join(seriesInfo['upfronts'])

		# Cast / Crew
		if 'cast' in seriesInfo:
			glue = "\n"
			infoText += "\n\nCast:\n%s" % glue.join(seriesInfo['cast']).encode('utf-8')
		return infoText

	def getEpisodeInfo(self, id):
		infoText = ""
		try:
			episodeInfo = self.server.sp.cache.getEpisodeInfo(id)
		except:
			return infoText
		if 'season' in episodeInfo and 'episode' in episodeInfo:
			infoText += "Staffel: %s, Episode: %s\n" % (episodeInfo['season'], episodeInfo['episode'])

		# Title
		if 'title' in episodeInfo:
			infoText += "Titel: %s" % episodeInfo['title'].encode('utf-8')

		# Rating
		if 'rating' in episodeInfo and 'ratingCount' in episodeInfo:
			infoText += "\n\n"
			infoText += "Episodenbewertung: %.1f aus %s Stimmen" % (float(episodeInfo['rating']), episodeInfo['ratingCount'])

		# Transmissions
		infoText += "\n\n"
		if 'firstAired' in episodeInfo:
			infoText += "Erstausstrahlung: %s\n" % episodeInfo['firstAired']

		# Description
		if 'description' in episodeInfo:
			infoText += "\n"
			infoText += "%s\n" % episodeInfo['description'].encode('utf-8')

		# Cast / Crew
		if 'guestStars' in episodeInfo:
			glue = ", "
			infoText += "\n\nGaststars:\n%s" % glue.join(episodeInfo['guestStars']).encode('utf-8')
		if 'directors' in episodeInfo:
			glue = ", "
			infoText += "\n\nRegie:\n%s" % glue.join(episodeInfo['writers']).encode('utf-8')
		if 'writers' in episodeInfo:
			glue = ", "
			infoText += "\n\nDrehbuch:\n%s" % glue.join(episodeInfo['writers']).encode('utf-8')

		return infoText


	def doSearch(self, searchString, start = 0):
		more = 0
		resultList = []
		try:
			searchResults = self.server.sp.cache.searchSeries(searchString, start)
			for searchResult in searchResults['results']:
				resultList.append((searchResult['name'].encode('utf-8'), searchResult['country_year'].encode('utf-8'), str(searchResult['id'])))
			if 'more' in searchResults:
				more = int(searchResults['more'])
		except:
			resultList = []
		return start, more, resultList

	def doGetCoverURL(self, seriesID, seriesName):
		try:
			return self.server.sp.cache.getCoverURL(int(seriesID), seriesName)
		except:
			return ''
			
	def doGetWebChannels(self):
		return self.server.sp.cache.getWebChannels()

	def doGetPlanerData(self, offset, webChannels):
		return self.server.sp.cache.getNewPlanerData(int(offset), webChannels)

	def doGetTopThirty(self):
		return self.server.sp.cache.getTopTen()

	def doGetEpisodes(self, seriesID, page):
		return self.server.sp.cache.getEpisodes(int(seriesID), int(page))

	def doGetTransmissions(self, seriesID, offset, webChannels):
		resultList = []
		transmissions = self.server.sp.cache.getTransmissions(int(seriesID), int(offset), webChannels)
		seriesName = transmissions['series']

		for event in transmissions['events']:
			if event['season'] is '':
				event['season'] = '0'
			if event['episode'] is '':
				event['episode'] = '00'
			resultList.append([seriesName.encode('utf-8'), event['channel'].encode('utf-8'), event['start'], event['end'], event['season'], event['episode'], event['title'].encode('utf-8'), "0"])

		return resultList

	def doGetSeasonBegins(self, webChannels):
		return self.server.sp.cache.getSeasonBegins(webChannels)
