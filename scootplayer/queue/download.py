#!/usr/bin/env python2.7

from base import BaseQueue
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
            if (int(self.report['time_buffer']) + int(representation[0])) \
                    <= int(self.time_buffer_max):
                    self.report['time_buffer'] += int(representation[0])
                    self.queue.put((representation))
                    return
            else:
                time.sleep(1)

    def downloader(self):
        """Download the next item in the download queue."""
        while True:
            if self.run:
                item = self.queue.get()
                self.report['bandwidth'] = item[4]
                self.report['id'] = int(item[5])
                _, length = self.player.fetch_item(item)
                self.player.item_ready(item)
                self.queue.task_done()
                self.report['time_buffer'] = self.report['time_buffer'] - \
                    int(item[0])
            else:
                time.sleep(1)

    def __len__(self):
        """Return the current length of the download queue."""
        return self.queue.qsize()
