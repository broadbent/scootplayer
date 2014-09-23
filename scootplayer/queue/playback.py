#!/usr/bin/env python2.7

from base import BaseQueue
import time


class PlaybackQueue(BaseQueue):
    """Object which acts as a playback queue for the player."""

    def __init__(self, *args, **kwargs):
        """
        Initialise playback queue with minimum and maximum buffer sizes.

        """
        super(PlaybackQueue, self).__init__(*args, **kwargs)
        self.stats = dict(average_occupancy=0, min_bandwidth=0, max_bandwidth=0,
                          average_bandwidth=0, bandwidth_changes=0)
        self.report = dict(time_buffer=0, bandwidth=0, id=0, time_position=0)
        self.start = False
        self._previous_bandwidth = 0
        self._items_played = 0
        self._total_bandwidth = 0

    def stop(self):
        """Stop the playback queue."""
        self.queue.queue.clear()
        self.player.event('stop', 'playback')

    def add(self, representation):
        """Add an item to the playback queue."""
        while True:

            if (int(self.report['time_buffer']) + int(representation[0])) \
                    <= int(self.time_buffer_max) and self.run:
                self.report['time_buffer'] += int(representation[0])
                self.queue.put((representation))
                if self.start is True and self.report['time_buffer']  \
                        >= self.time_buffer_min:
                    self.player.event('start', 'playback')
                    self.start = True
                    self.player.start_thread(self.playback)
                return
            else:
                time.sleep(1)

    def playback(self):
        """Consume the next item in the playback queue."""
        self.report['time_position'] = 0
        while True:
            if self.report['time_buffer'] > 0 and self.run:
                item = self.queue.get()
                self.report['time_position'] += int(item[0])
                self.report['bandwidth'] = int(item[4])
                self.report['id'] = int(item[5])
                self._consume_chunk(item[0])
                self.queue.task_done()
                self.report['time_buffer'] = self.report['time_buffer'] - \
                    int(item[0])
            else:
                time.sleep(1)

    def _consume_chunk(self, duration):
        while duration > 0:
            if self.run:
                duration = duration - 1
                self.player.bar.next(1)
            time.sleep(1)

    def bandwidth_analysis(self):
        if self.stats['min_bandwidth'] == 0:
            self.stats['min_bandwidth'] = self.report['bandwidth']
        if self.report['bandwidth'] != self._previous_bandwidth:
            self.stats['bandwidth_changes'] += 1
        if self.report['bandwidth'] > self.stats['max_bandwidth']:
            self.stats['max_bandwidth'] = self.report['bandwidth']
        elif self.report['bandwidth'] < self.stats['min_bandwidth']:
            self.stats['min_bandwidth'] = self.report['bandwidth']
        self._items_played += 1
        self._total_bandwidth += self.report['bandwidth']
        self.stats['average_bandwidth'] = self._total_bandwidth / \
            self._items_played
        self._previous_bandwidth = self.report['bandwidth']

    def __len__(self):
        """Return the current length of the playback queue."""
        return self.queue.qsize()
