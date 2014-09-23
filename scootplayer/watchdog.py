#!/usr/bin/env python2.7

import time


class Watchdog(object):

    watch_value = 0
    watch_count = False
    max_duration = 0
    run = False

    def __init__(self, player):
        self.player = player
        self.player.start_thread(self.wait_for_max_duration)

    def wait_for_max_duration(self):
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
        self.run = False

    def resume(self):
        self.run = True

    def watchdog(self):
        if self.run:
            self.player.start_timed_thread(self.max_duration, self.watchdog)
            try:
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
            except Exception as e:
                print e
        else:
            time.sleep(self.max_duration)
            self.watchdog()

    def _dump(self):
        self.player.create_directory('/dump')
        self._dump_object('player', self.player)
        self._dump_threads()

    def _dump_object(self, title, _object):
        file = self.player.open_file('/dump/' + title + '.txt')
        try:
            for key, value in _object.__dict__.items():
                if key in ['representations', 'bandwidth', 'playback_queue',
                           'download_queue', 'reporter', 'remote_control',
                           'queue']:
                    self._dump_object(key, value)
                file.write(key + ',' + str(value) + '\n')
        except:
            pass

    def _dump_threads(self):
        file = self.player.open_file('/dump/threads.txt')
        for thread in self.player.threads:
            if thread.isAlive():
                file.write(str(thread) + '\n')
