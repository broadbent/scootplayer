#!/usr/bin/env python2.7

"""Queue used to emulate the player playing back downloaded content."""

from .base import BaseQueue
import time


class PlaybackQueue(BaseQueue):

    """Object which acts as a playback queue for the player."""

    def __init__(self, *args, **kwargs):
        """
        Initialise playback queue with minimum and maximum buffer sizes.

        """
        super(PlaybackQueue, self).__init__(*args, **kwargs)
        self.start = False

    def stop(self):
        """Stop the playback queue."""
        self.queue.queue.clear()
        self.player.event('stop', 'playback')

    def add(self, representation):
        """Add an item to the playback queue."""
        while True:
            if (int(self.report['time_buffer'])
                    + int(representation['item'][0])) \
                    <= int(self.time_buffer_max) and self.run:
                self.report['time_buffer'] += int(representation['item'][0])
                self.queue.put((representation))
                if self.start != True and self.report['time_buffer'] \
                        >= self.time_buffer_min:
                    self.player.event('start', 'playback')
                    self.start = True
                    self.player.start_thread(self.playback)
                return
            else:
                time.sleep(0.1)

    def playback(self):
        """Consume the next item in the playback queue."""
        self.report['time_position'] = 0
        while True:
            if self.report['time_buffer'] > 0 and self.run:
                item = self.queue.get()
                if self.player.options.url:
                    self._url_parser(item['item'][1])
                self.report['time_position'] += int(item['item'][0])
                self.report['bandwidth'] = int(item['bandwidth'])
                self.report['max_encoded_bitrate'] = item[
                    'max_encoded_bitrate']
                self.report['id'] = int(item['id'])
                self._consume_chunk(item['item'][0])
                self.queue.task_done()
                self.report['time_buffer'] = self.report[
                    'time_buffer'] - int(item['item'][0])
            elif self.report['time_buffer'] <= 0:
                self.player.finish_playback()
            else:
                time.sleep(0.1)

    def _consume_chunk(self, duration):
        """
        Ensure that an appropriate amount of time has elapsed before
        progressing onto next chunk.

        """
        while duration > 0:
            if self.run:
                duration = duration - 1
                self.player.progress_bar.next(1)
            time.sleep(1)

    def __len__(self):
        """Return the current length of the playback queue."""
        return self.queue.qsize()
