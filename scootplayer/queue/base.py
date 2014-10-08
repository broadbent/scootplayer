#!/usr/bin/env python2.7

"""Base class for the different queues used in Scootplayer."""

import Queue
import re


class BaseQueue(object):

    """A set of common functions used on the queue classes of Scootplayer."""

    window_size = 5

    def __init__(self, *args, **kwargs):
        """Initialise a queue object with default values."""
        self.occupancy = []
        self.bandwidth = []
        self.stats = dict(mean_average_occupancy=0, min_bandwidth=0,
                          max_bandwidth=0, mean_average_bandwidth=0,
                          bandwidth_changes=0)
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
        self.occupancy.append(self.report['time_buffer'])
        self.stats['mean_average__occupancy'] = average(self.occupancy)

    def _url_parser(self, url):
        """Parse the URL to unreliably(!) determine the playback bitrate."""
        pattern = re.compile(ur'.*\_(.*kbit).*')
        match = re.match(pattern, url)
        self.report['url_bitrate'] = match.group(1).replace('kbit', '')

    def analysis(self):
        """Run both analysis methods on a queue object."""
        self._queue_analysis()
        self._bandwidth_analysis()

    def _bandwidth_analysis(self):
        """
        Analyse the current bandwidth.

        Update the minimum, maximum, and amount of bandwidth changes.

        Calculate the arithmetic mean for the whole period of playback
        and for the n most recent bandwidth values.

        """
        if self.stats['min_bandwidth'] == 0:
            self.stats['min_bandwidth'] = self.report['bandwidth']
        if self.report['bandwidth'] != self._previous_bandwidth:
            self.stats['bandwidth_changes'] += 1
        if self.report['bandwidth'] > self.stats['max_bandwidth']:
            self.stats['max_bandwidth'] = self.report['bandwidth']
        elif self.report['bandwidth'] < self.stats['min_bandwidth']:
            self.stats['min_bandwidth'] = self.report['bandwidth']
        self.bandwidth.append(self.report['bandwidth'])
        self.stats['mean_average_bandwidth'] = average(self.bandwidth)
        self.report['moving_average_bandwidth'] = average(
            self.bandwidth[-self.window_size:])
        self._previous_bandwidth = self.report['bandwidth']

def average(list_):
    """Calculate an arithmetic mean for a List of values."""
    try:
        return sum(list_) / len(list_)
    except ZeroDivisionError:
        return 0

