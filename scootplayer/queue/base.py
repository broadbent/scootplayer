#!/usr/bin/env python2.7

import Queue


class BaseQueue(object):

    def __init__(self, *args, **kwargs):
        self.occupancy = []
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
        self.stats['average_occupancy'] = sum(self.occupancy) / \
            len(self.occupancy)
