#!/usr/bin/env python2.7

"""scootplayer.py - experimental MPEG-DASH request engine with support for accurate logging."""

import xml.etree.ElementTree as ET
import time
import threading
import Queue
import urllib2
import optparse
import os
import shutil

class Player():

	representations = None
	bandwidth = None
	playback_queue = None
	download_queue = None
	reporter = None	
	options = None
	directory = None

	def __init__(self, options):
		self.start_time = time.time()
		self.options = options
		time_now = str(int(time.time()))
		self.directory = self.options.output + time_now
		self.create_directory(self.directory + '/downloads')
		self.reporter = self.Reporter(self)
		self.bandwidth = self.Bandwidth()
		self.representations = self.Representations(self, self.options.manifest)
		self.playback_queue = self.PlaybackQueue(self, self.representations.min_buffer)
		self.download_queue = self.DownloadQueue(self)
		self.start_playback()

	def create_directory(self, path):
		if not os.path.exists(path):
			os.makedirs(path)

	def remove_directory(self, path):
		if os.path.exists(path):
			shutil.rmtree(path)

	def start_playback(self):
		playback_marker = 0
		duration = 1
		self.reporter.event('start', 'adding representations')
		while True:
			representation = self.representations.candidate(self.bandwidth.current)
			try:
				duration = representation[1][playback_marker/duration][0]
				self.download_queue.add(representation[1][playback_marker/duration])
			except IndexError:
				self.reporter.event('stop', 'adding representations')
				return
			playback_marker += duration

	def make_request(self, item):
		request = urllib2.Request(item[1])
		if item[3] != 0:
			request.headers['Range'] = 'bytes=%s-%s' % (item[2], item[3])
		response = urllib2.urlopen(request)
		return response

	def write_to_file(self, item, response):
		content = response.read()
		file_name = item[1].split('/')[-1]
		full_path = self.directory + '/downloads/' + file_name
		file_start = int(item[2])
		file_end = int(item[3])
		try:
			_file = open(full_path,  'r+')
		except IOError:
			_file = open(full_path,  'w')
		_file.seek(int(item[2]))
		_file.write(content)
		file_pointer = int(_file.tell()-1)
		if file_end != file_pointer and file_start != 0:
			print 'ends do not match'
		_file.close()

	def update_bandwidth(self, duration, length):
		self.bandwidth.change(int(length/duration))

	def stop(self):
		self.download_queue.stop()
		self.playback_queue.stop()
		self.reporter.stop()
		os._exit(0)

	class Reporter():

		player = None
		start_time = 0
		report_file = None
		event_file = None
		report = False

		def __init__(self, player):
			self.player = player
			file_name = self.player.directory + '/report.csv'
			self.report_file = open(file_name, 'w')
			file_name = self.player.directory + '/event.csv'
			self.event_file = open(file_name, 'w')
			self.start()

		def stop(self):
			self.report = False
			time.sleep(1)
			self.report_file.close()
			self.event_file.close()

		def start(self):
			self.report = True
			self.start_time = time.time()
			threading.Thread(target=self.reporter, args=()).start()

		def time_elapsed(self):
			return round(time.time() - self.start_time, 4)

		def reporter(self):
			if self.report:
				threading.Timer(interval=int(1), function=self.reporter, args=()).start()
			time_elapsed = self.time_elapsed()
			try:
				self.report_file.flush()
			except Exception:
				pass
			try:
				self.report_file.write(str(time_elapsed) + "," + str(self.player.download_queue.time_buffer) + "," + str(self.player.download_queue.bandwidth) + "," +  
					str(self.player.download_queue._id) + "," + str(self.player.playback_queue.time_buffer) + "," + str(self.player.playback_queue.time_position) + "," + 
					str(self.player.playback_queue.bandwidth) + "," + str(self.player.playback_queue._id)  + "," + str(self.player.bandwidth.current) + "\n")
			except Exception:
				self.report_file.write(str(time_elapsed) + str(', 0, 0, 0, 0, 0, 0, 0\n'))
			try:
				self.report_file.flush()
			except Exception:
				pass

		def event(self, action, description):
			threading.Thread(target=self.event_thread, args=(action, description)).start()

		def event_thread(self, action, description):
			time_elapsed = self.time_elapsed()
			try:
				self.event_file.flush()
			except Exception:
				pass
			self.event_file.write(str(time_elapsed) +  "," + str(action) + "," + str(description) + "\n")
			self.event_file.flush()

	class Representations():

		representations = None
		initialisations = None
		min_buffer = 0
		player = None

		def __init__(self, player, manifest):
			self. player = player
			self.representations = list()
			self.initialisations = list()
			self.parse_mpd(manifest)
			self.initialise()

		def parse_mpd(self, manifest):
			self.player.reporter.event('start', 'parsing mpd')
			xml = ET.parse(manifest)
			mpd = xml.getroot()
			base_url = self.BaseURL()
			self.min_buffer = int(float(mpd.attrib['minBufferTime'][2:-1]))
			for child in mpd:
				if 'BaseURL' in child.tag:
					base_url.mpd = child.text
				for child in child:
					if 'BaseURL' in child.tag:
						base_url.period = child.text
					for child in child:
						if 'BaseURL' in child.tag:
							base_url.adaption_set = child.text
						if 'Representation' in child.tag:
								bandwidth = int(child.attrib['bandwidth'])
								_id = int(child.attrib['id'])
						for child in child:
							if 'SegmentBase' in child.tag:
								for child in child:
									if 'Initialization' in child.tag:
										try:
											media_range = child.attrib['range'].split('-')
										except KeyError:
											media_range = (0, 0)
										self.initialisations.append((None, base_url.resolve() + child.attrib['sourceURL'],
											int(media_range[0]), int(media_range[1]) ))
							if 'BaseURL' in child.tag:
								base_url.representation = child.text
							if 'SegmentList' in child.tag:
								duration = int(child.attrib['duration'])
								playlist = list()
								for child in child:
									if 'SegmentURL' in child.tag:
										try:
											media_range = child.attrib['mediaRange'].split('-')
										except KeyError:
											media_range = (0, 0)
										playlist.append( (duration, base_url.resolve() + child.attrib['media'],
											int(media_range[0]), int(media_range[1]), int(bandwidth), int(_id) ))
								self.representations.append( (bandwidth, playlist) )
						base_url.representation = ''
					base_url.adaption_set = ''
				base_url.period = ''
			base_url.mpd = ''
			sorted(self.representations, key=lambda representation: representation[0])
			self.player.reporter.event('stop', 'parsing mpd')	

		def initialise(self):
			self.player.reporter.event('start', 'downloading initializations')
			total_duration = 0
			total_length = 0
			for item in self.initialisations:
				start = time.time()
				response = self.player.make_request(item)
				duration = time.time() - start
				length = float(response.headers.get('Content-Length'))
				self.player.write_to_file(item, response)
				self.player.update_bandwidth(duration, length)
				total_duration += duration
				total_length += float(response.headers.get('Content-Length'))
			self.player.update_bandwidth(total_duration, total_length)
			self.player.reporter.event('stop ', 'downloading initializations')

		def candidate(self, bandwidth):
			candidate_index = min(range(len(self.representations)), key=lambda 
				i: abs(self.representations[i][0]-int(bandwidth)))
			return self.representations[candidate_index]

		class BaseURL():

			representation = ''
			adaption_set = ''
			period = ''
			mpd = ''

			def resolve(self):
				if self.representation != str(''):
					return self.representation
				elif self.adaption_set != str(''):
					return self.adaption_set
				elif self.period != str(''):
					return self.period
				elif self.mpd != str(''):
					return self.mpd
				else:
					return str('')

	class DownloadQueue():

		queue = Queue.Queue()
		time_buffer_max = 30
		time_buffer = 0
		player = None
		bandwidth = 0
		_id = 0

		def __init__(self, player):
			self.player = player
			threading.Thread(target=self.downloader, args=()).start()

		def stop(self):
			self.player.reporter.event('final', 'download queue')

		def add(self, representation):
			while True:
				if (int(self.time_buffer) + int(representation[0])) <= int(self.time_buffer_max):
					self.time_buffer += int(representation[0])
					self.queue.put((representation))
					return

		def downloader(self):
			while True:
				item = self.queue.get()
				self.bandwidth = item[4]
				self._id = int(item[5])
				start = time.time()
				response = self.player.make_request(item)
				duration = time.time() - start
				length = float(response.headers.get('Content-Length'))
				self.player.write_to_file(item, response)
				self.player.update_bandwidth(duration, length)
				self.player.playback_queue.add(item)
				self.queue.task_done()
				self.time_buffer = self.time_buffer - int(item[0])

		def __len__(self):
			return self.queue.qlen()

	class PlaybackQueue():

		queue = Queue.Queue()
		bandwidth = 0
		_id = 0
		time_buffer_min = 0
		time_buffer_max = 60
		time_buffer = 0
		time_position = 0
		start = False
		player = None

		def __init__(self, player, min_buffer):
			self.player = player
			self.time_buffer_min = min_buffer

		def stop(self):
			self.player.reporter.event('final', 'playback queue')

		def add(self, representation):
			while True:
				if (int(self.time_buffer) + int(representation[0])) <= int(self.time_buffer_max):
					self.time_buffer += int(representation[0])
					self.queue.put((representation))
					if self.start != True and self.time_buffer >= self.time_buffer_min:
						self.player.reporter.event('start', 'playback')
						self.start = True
						threading.Thread(target=self.playback, args=()).start()
					return

		def playback(self):
			self.time_position = 0
			while self.time_buffer > 0:
				item = self.queue.get()
				self.time_position += int(item[0])
				self.bandwidth = int(item[4])
				self._id = int(item[5])
				time.sleep(int(item[0]))
				self.queue.task_done()
				self.time_buffer = self.time_buffer - int(item[0])
			self.player.reporter.event('stop', 'playback')
			self.player.stop()

		def __len__(self):
			return self.queue.qlen()

	class Bandwidth():

		current = 0
		previous = 0
		trend = 0

		def change(self, bandwidth):
			self.previous = self.current
			self.current  = bandwidth
			if self.current > self.previous:
				self.trend = 1
			elif self.current == self.previous:
				self.trend = 0
			elif self.current < self.previous:
				self.trend = -1

		def __str__(self):
			return str(self.current)

if __name__ == '__main__':
	parser = optparse.OptionParser()
	parser.add_option("-m", "--manifest", dest="manifest",
	    help="location of manifest to load")
	parser.add_option("-o", "--output", dest="output", default="out/",
	    help="location to store downloaded files and reports")
	(options, args) = parser.parse_args()
	if options.manifest != None:
		player = Player(options)
	else:
		parser.print_help()