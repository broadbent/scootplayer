#!/usr/bin/env python2.7

"""Functions as a list of manifests to be played back in order."""

from .base import BaseQueue


class PlaylistQueue(BaseQueue):

    """Functions as a list of manifests to be played back in order."""

    def __init__(self, *args, **kwargs):
        """Initialise download queue with max size and start thread."""
        super(PlaylistQueue, self).__init__(*args, **kwargs)
        if self.options.playlist:
            playlist = self.parse_playlist_file(self.options.playlist)
            for manifest in playlist:
                self.add(manifest)
        elif self.options.manifest:
            self.add(self.options.manifest)

    def stop(self):
        """Clear the playlist queue."""
        self.queue.queue.clear()
        self.player.event('stop', 'playlist')

    def add(self, manifest):
        """Add a manifest item to the playlist queue."""
        self.queue.put(manifest)

    def get(self):
        """Get the next item from the playlist queue."""
        return self.queue.get()

    def done(self):
        """Mark the current item as finished."""
        self.queue.task_done()

    def empty(self):
        """Return if the playlist queue is empty or not."""
        return self.queue.empty()

    def __len__(self):
        """Return the current length of the playlist queue."""
        return self.queue.qsize()

    def parse_playlist_file(self, path):
        """Open and parse the M3U playlist file."""
        file = open(path, 'r')
        line = file.readline()
        playlist = []
        if not line.startswith('#EXTM3U'):
            self.player.event('error', 'M3U playlist not valid')
            return
        for line in file:
            line = line.strip()
            if (len(line) != 0):
                playlist.append(line)
        file.close()
        return playlist
