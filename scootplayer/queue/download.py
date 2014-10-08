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
		    + int(representation['item'][0])) \
                    <= int(self.time_buffer_max):
                self.report['time_buffer'] += int(representation['item'][0])
                self.queue.put((representation))
                return
            else:
                time.sleep(1)

    def downloader(self):
        """Download the next item in the download queue."""
        while True:
            if self.run:
                item = self.queue.get()
                if self.player.options.url:
                    self._url_parser(item['item'][1])
                self.report['bandwidth'] = item['bandwidth']
                self.report['max_encoded_bitrate'] = item[
                    'max_encoded_bitrate']
                self.report['id'] = int(item['id'])
                self.player.fetch_item(item['item'])
                self.player.item_ready(item)
                self.queue.task_done()
                self.report['time_buffer'] = self.report['time_buffer'] - \
                    int(item['item'][0])
            else:
                time.sleep(1)

    def __len__(self):
        """Return the current length of the download queue."""
        return self.queue.qsize()
