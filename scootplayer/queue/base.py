#!/usr/bin/env python2.7

import Queue

class BaseQueue(object):

    run = False
    queue = Queue.Queue()
    # __shared_state = {}

    def __init__(self, *args, **kwargs):
        # self.__dict__ = self.__shared_state
        self.queue.queue.clear()
        self.occupancy = []
        for key, val in kwargs.items():
            setattr(self, key, val)

    def queue_analysis(self):
        self.occupancy.append(self.report['time_buffer'])
        self.stats['average_occupancy'] = sum(self.occupancy) / len(self.occupancy)
