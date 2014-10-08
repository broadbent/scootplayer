#!/usr/bin/env python2.7

"""Inspects player behaviour to ensure playback is occuring."""

import time


class Watchdog(object):

    """Aids in debugging issues caused by stalled playback."""

    watch_value = 0
    watch_count = False
    max_duration = 0
    run = False

    def __init__(self, player):
        """Start thread to wait for max duration to become available."""
        self.player = player
        self.player.start_thread(self.wait_for_max_duration)

    def wait_for_max_duration(self):
        """
        Get maximum segment duration of current MPD. If not available, wait and
        try again.

        When this value is available, start the watchdog thread proper.

        """
        try:
            self.max_duration = self.player.max_duration()
            self.player.start_thread(self.watchdog)
        except AttributeError:
            self.player.start_timed_thread(1, self.wait_for_max_duration)

    def stop(self):
        """Stop watching."""
        self.run = False
        self.player.event('stop', 'watchdog')

    def pause(self):
        """Pause watching."""
        self.run = False

    def resume(self):
        """Resume watching."""
        self.run = True

    def watchdog(self):
        """
        Periodically monitor playback to ensure that it is progressing.

        If playback stops for any reason, dump the current set of objects to
        file for analysis and debug.

        """
        if self.run:
            self.player.start_timed_thread(self.max_duration, self.watchdog)
            report = self.player.retrieve_metric('report')
            if self.watch_value == 0:
                try:
                    report = self.player.report()
                    self.watch_value = report['playback_time_position']
                except AttributeError:
                    pass
            if self.watch_value == report['playback_time_position']:
                if self.watch_count:
                    self.player.event('error',
                                      'detected stalled playback')
                    self._dump()
                    self.player.exit()
                self.watch_count = True
            else:
                self.watch_count = False
            self.watch_value = report['playback_time_position']
        else:
            time.sleep(self.max_duration)
            self.watchdog()

    def _dump(self):
        """
        Dump each object to file.

        Also dumps a list of threads with their statuses.

        """
        self.player.create_directory('/dump')
        self._dump_object('player', self.player)
        self._dump_threads()

    def _dump_object(self, title, object_):
        """
        Recursively dump each object to file.

        Starts with the main player and recurses downwards.

        """
        file_ = self.player.open_file('/dump/' + title + '.txt')
        for key, value in object_.__dict__.items():
            if key in ['representations', 'bandwidth', 'playback_queue',
                       'download_queue', 'reporter', 'remote_control',
                       'queue']:
                self._dump_object(key, value)
            file_.write(key + ',' + str(value) + '\n')

    def _dump_threads(self):
        """Dump the name and status of each thread registered in the player."""
        file_ = self.player.open_file('/dump/threads.txt')
        for thread in self.player.threads:
            if thread.isAlive():
                file_.write(str(thread) + '\n')
