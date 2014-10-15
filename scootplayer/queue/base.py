#!/usr/bin/env python2.7

"""Base class for the different queues used in Scootplayer."""

import Queue
import re
import numpy as np


class BaseQueue(object):

    """A set of common functions used on the queue classes of Scootplayer."""

    window_size = 5

    def __init__(self, *args, **kwargs):
        """Initialise a queue object with default values."""
        self.occupancy = []
        self.bandwidth = []
        self.url_bitrate = []
        self.stats = dict()
        self.report = dict(time_buffer=0, bandwidth=0, id=0, time_position=0,
                           moving_average_bandwidth=0, max_encoded_bitrate=0,
                           url_bitrate=0)
        self._previous_bandwidth = 0
        for key, val in kwargs.items():
            setattr(self, key, val)
        self.run = False
        self.queue = Queue.Queue()

    def pause(self):
        """Pause the operation of a queue."""
        self.run = False

    def resume(self):
        """Resume the operation of a queue."""
        self.run = True

    def _queue_analysis(self):
        """Analyse the occupancy of a queue."""

    def _url_parser(self, url):
        """Parse the URL to unreliably(!) determine the playback bitrate."""
        pattern = re.compile(ur'.*\_(.*kbit).*')
        match = re.match(pattern, url)
        self.report['url_bitrate'] = int(match.group(1).replace('kbit', ''))
        self.url_bitrate.append(self.report['url_bitrate'])
        self._object_analysis('url_bitrate', self.url_bitrate)

    def report_tick(self):
        """
        Called periodically by the player on a fixed interval.

        Append the latest values of bandwidth and occupancy to the object lists.
        Run the periodic statistical analysis of the bandwidth and occupancy
        lists.

        """
        self.bandwidth.append(self.report['bandwidth'])
        self.occupancy.append(self.report['time_buffer'])
        self._report_analysis('occupancy', self.occupancy)
        self._report_analysis('bandwidth', self.bandwidth)

    def calculate_stats(self):
        """Run fianl statistical analysis on the bandwidth and occupancy lists."""
        self._stats_analysis('occupancy', self.occupancy)
        self._stats_analysis('bandwidth', self.bandwidth)

    def _report_analysis(self, name, object_):
        """Calculate the moving average using NumPy."""
        self.report['moving_average_' + name] = np.average(object_[-self.window_size:])

    def _stats_analysis(self, name, object_):
        """Calculate various statistics using NumPy."""
        self.stats['min_' + name] = np.amin(object_)
        self.stats['max_' + name] = np.amax(object_)
        self.stats['changes_' + name] = self._changes(object_)
        self.stats['average_' + name] = np.average(object_)
        self.stats['std_' + name] = np.std(object_)
        self.stats['var_' + name] = np.var(object_)

    def _changes(self, list_):
        """Count the number of changes in a list object."""
        prev = list_[0]
        count = 0
        for item in list_[1:]:
            if not item == prev:
                count += 1
            prev = item
        return count
