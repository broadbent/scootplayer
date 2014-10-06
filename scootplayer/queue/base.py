#!/usr/bin/env python2.7

import Queue
import itertools


class BaseQueue(object):

    def __init__(self, *args, **kwargs):
        self.occupancy = []
	self.bandwidth = []
	self.stats = dict(mean_average_occupancy=0, min_bandwidth=0, max_bandwidth=0,
                          mean_average_bandwidth=0, bandwidth_changes=0)
        self.report = dict(time_buffer=0, bandwidth=0, id=0, time_position=0, 
			   moving_average_bandwidth=0, max_encoded_bitrate=0)
        self._previous_bandwidth = 0
	for key, val in kwargs.items():
            setattr(self, key, val)
        self.run = False
        self.queue = Queue.Queue()

    def pause(self):
        self.run = False

    def resume(self):
        self.run = True

    def queue_analysis(self):
        self.occupancy.append(self.report['time_buffer'])
	self.stats['mean_average_occupancy'] = self._average(self.occupancy)

    def _average(self, _list):
	try:
	    return sum(_list) / len(_list)
	except ZeroDivisionError:
		return 0

    def bandwidth_analysis(self):
        if self.stats['min_bandwidth'] == 0:
            self.stats['min_bandwidth'] = self.report['bandwidth']
        if self.report['bandwidth'] != self._previous_bandwidth:
            self.stats['bandwidth_changes'] += 1
        if self.report['bandwidth'] > self.stats['max_bandwidth']:
            self.stats['max_bandwidth'] = self.report['bandwidth']
        elif self.report['bandwidth'] < self.stats['min_bandwidth']:
            self.stats['min_bandwidth'] = self.report['bandwidth']
	self.bandwidth.append(self.report['bandwidth'])
	self.stats['mean_average_bandwidth'] = self._average(self.bandwidth)
        self.report['moving_average_bandwidth'] = self._average(self.bandwidth[-self.window_size:])
        self._previous_bandwidth = self.report['bandwidth']

