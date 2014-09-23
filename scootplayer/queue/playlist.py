#!/usr/bin/env python2.7

import base

class PlaylistQueue(base.BaseQueue):

    __shared_state = {}

    def __init__(self, player, options):
        """Initialise download queue with max size and start thread."""
        self.__dict__ = self.__shared_state
        self.player = player
        if options.playlist:
            playlist = self._parse_playlist_file(options.playlist)
            for manifest in playlist:
                self.add(manifest)
        elif options.manifest:
            self.add(options.manifest)

    def _parse_playlist_file(self, path):
        playlist = self._load_playlist_file(path)
        playlist = re.split(r'(\n)', playlist)
        return playlist

    def _load_playlist_file(self, path):
        _file = open(path, 'r')
        return _file.read()

    def stop(self):
        """Stop the download queue."""
        self.queue.queue.clear()
        self.player.event('stop', 'playlist')

    def add(self, manifest):
        self.queue.put(manifest)

    def get(self):
        return self.queue.get()

    def done(self):
        self.queue.task_done()

    def empty(self):
        return self.queue.empty()

    def __len__(self):
        """Return the current length of the download queue."""
        return self.queue.qsize()
