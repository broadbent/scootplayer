#!/usr/bin/env python2.7

"""Queue used to regulate segment downloads."""

from .base import BaseQueue
import time


class DownloadQueue(BaseQueue):

    """Object which acts as a download queue for the player."""

    def __init__(self, *args, **kwargs):
        """Initialise download queue with max size and start thread."""
        super(DownloadQueue, self).__init__(*args, **kwargs)
        self.player.create_directory('/downloads')
        self.player.start_thread(self.downloader)

    def stop(self):
        """Stop the download queue."""
        self.queue.queue.clear()
        self.player.event('stop', 'download')

    def add(self, representation):
        """Add an item to the download queue."""
        while self.run:
            if (int(self.report['time_buffer'])
		    + int(representation['item']['duration'])) \
                    <= int(self.time_buffer_max):
                self.report['time_buffer'] += int(
                    representation['item']['duration'])
                self.queue.put((representation))
                return
            else:
                time.sleep(0.01)

    def downloader(self):
        """Download the next item in the download queue."""
        while True:
            if self.run:
                representation = self.queue.get()
                if self.player.options.url:
                    self._url_parser(representation['item']['url'])
                self.report['bandwidth'] = representation['bandwidth']
                self.report['max_encoded_bitrate'] = representation[
                    'max_encoded_bitrate']
                self.report['id'] = int(representation['id'])
                self.player.fetch_item((representation['item']))
                self.player.item_ready(representation)
                self.queue.task_done()
                self.report['time_buffer'] = self.report['time_buffer'] - \
                    int(representation['item']['duration'])
            else:
                time.sleep(0.01)

    def __len__(self):
        """Return the current length of the download queue."""
        return self.queue.qsize()
