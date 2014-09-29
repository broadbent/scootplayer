#!/usr/bin/env python2.7

"""Experimental MPEG-DASH player emulator."""

import os
import Queue
import requests
import shutil
import signal
import sys
import threading
import time

import scootplayer.bandwidth as bandwidth
import scootplayer.queue as queue
import scootplayer.remote as remote
import scootplayer.reporter as reporter
import scootplayer.representations as representations
import scootplayer.watchdog as watchdog
import scootplayer.progressbar as progressbar

class Player(object):

    bandwidth = None
    managed_objects = {'download': None,
                       'playback': None,
                       'download': None,
                       'playlist': None,
                       'representations': None,
                       'reporter': None,
                       'watchdog': None,
                       'remote_control': None}
    session = None
    threads = list()
    finished = False

    def __init__(self, options):
        """Initialise the player and start playback."""
        self.options = options
        self._setup_signal_handling()
        self.managed_objects['remote_control'] = remote.RemoteControl(
            self, options)
        self.managed_objects['playlist'] = queue.playlist.PlaylistQueue(
            player=self, options=options)
        self.next()
        self._consumer()

    def next(self):
        """Move onto the next item in the playlist, resetting everything."""
        self.finished = False
        self._directory_setup()
        self.managed_objects['reporter'] = reporter.Reporter(self)
        self.pause()
        self.session = requests.Session()
        self.bandwidth = bandwidth.Bandwidth()
        manifest = self.managed_objects['playlist'].get()
        self.managed_objects['download'] = queue.download.DownloadQueue(
            player=self, time_buffer_max=int(self.options.max_download_queue))
        self.managed_objects['representations'] = \
            representations.Representations(self, manifest)
        self.bar = self.create_progress_bar()
        self.managed_objects['playback'] = queue.playback.PlaybackQueue(
            player=self, time_buffer_min=int(
                self.managed_objects['representations'].min_buffer),
            time_buffer_max=int(self.options.max_playback_queue))
        self.managed_objects['watchdog'] = watchdog.Watchdog(self)
        self._setup_scheduled_stop(self.options.playback_time)
        self.resume()

    def _directory_setup(self):
        """Create directory for storing downloads"""
        time_now = str(int(time.time()))
        self.directory = self.options.output + '/' + time_now
        self.create_directory()

    def _consumer(self):
        while True:
            self.bar.next(0)
            if self.state == 'play':
                representation = self.managed_objects['representations'] \
                    .candidate(int(self.bandwidth))
                self.managed_objects['download'].add(representation)
                if self.finished:
                    self.next()
            else:
                time.sleep(1)

    def _setup_scheduled_stop(self, time):
        if time:
            self.start_timed_thread(time, self.exit)

    def finish_playback(self):
        self.finished = True

    def exit(self):
        self.state = 'exit'
        self.stop()
        os._exit(0)  # TODO: No cleanup on exit
        # sys.exit(0)

    def pause(self):
        self.state = 'pause'
        self._modify_state('pause')

    def resume(self):
        self.state = 'play'
        self._modify_state('resume')

    def stop(self):
        """Stop playback of scootplayer."""
        self.state = 'stop'
        self.bar.suffix = '0:00 / 0:00 / stop'
        self.bar.next(0)
        self._modify_state('stop')

    def _modify_state(self, method=None):
        for _, val in self.managed_objects.items():
            try:
                getattr(val, method)()
            except AttributeError:
                pass

    def _setup_signal_handling(self):
        """Setup interrupt signal handling."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle interrupt signals from user."""
        self.exit()

    def make_request(self, item):
        """Make a HTTP request for a single item within the playback queue."""
        url = item[1]
        headers = {}
        if item[3] != 0:
            byte_range = 'bytes=%s-%s' % (item[2], item[3])
            headers['Range'] = byte_range
        response = self.session.get(url, headers=headers)
        if not self.options.keep_alive:
            response.connection.close()
        return response

    def open_file(self, path):
        """Open a file and return the file handle."""
        file_name = self.directory + path
        return open(file_name, 'w')

    def fetch_item(self, item):
        """Fetch an individual item from a remote location.

        Writes the item to file. Also updates the bandwidth based upon the
        duration of the transaction and the amount of bits received in that
        time.

        Returns:
            duration: time taken to fulfil the request
            length: response length for use with the MPD '@bandwidth' value
                (in bits).
        """
        response, duration = self._time_request(item)
        self._check_code(response.status_code, item[1])
        length = self._get_length(response)
        self.write_to_file(item, response)
        self.update_bandwidth(duration, length)
        return duration, length

    def item_ready(self, item):
        self.managed_objects['playback'].add(item)

    def retrieve_metric(self, metric):
        result = {}
        for obj in ['download', 'playback']:
            for key, val in self.managed_objects[obj].__dict__[metric].items():
                result[obj + '_' + key] = val
        return result

    def max_duration(self):
        return self.managed_objects['representations'].max_duration

    def analysis(self):
        try:
            self.managed_objects['playback'].bandwidth_analysis()
            self.managed_objects['playback'].queue_analysis()
            self.managed_objects['download'].queue_analysis()
        except AttributeError:
                pass  # Download and playback queues not yet initialised

    def _time_request(self, item):
        """Makes request and times response."""
        start = time.time()
        response = self.make_request(item)
        duration = time.time() - start
        return response, duration

    def _check_code(self, code, url):
        """Checks if the request was successful (using the HTTP error code)"""
        if code >= 400:
            self.event('error', 'could not download '
                       + url + ' (code ' + str(code) + ')')
            raise SystemExit()

    def _get_length(self, response):
        """
        Get length of response from HTTP response header.

        Falls back to checking the length of the response content if value not
        present in header. Also ensures that we convert from octets to bits for
        use in the bandwidth estimation algorithm

        """
        try:
            length = int(response.headers.get('Content-Length'))
        except TypeError:
            length = len(response.content)
        length = length * 8
        return length

    def write_to_file(self, item, response):
        """
        Write response content to file.

        This may be a complete file, or a byte range to an existing file.

        """
        content = response.content
        file_name = item[1].split('/')[-1]
        full_path = self.directory + '/downloads/' + file_name
        file_start = int(item[2])
        file_end = int(item[3])
        try:
            _file = open(full_path, 'r+')
        except IOError:
            _file = open(full_path, 'w')
        _file.seek(int(item[2]))
        _file.write(content)
        file_pointer = int(_file.tell()-1)
        if file_end != file_pointer and file_start != 0:
            print 'ends do not match'
        _file.close()

    def update_bandwidth(self, duration, length):
        """Update the current bandwidth estimation."""
        if duration == 0 or length == 0:
            pass
        else:
            self.bandwidth.change(int(length/duration))

    def start_thread(self, target, args=(), **kwargs):
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
        return thread

    def start_timed_thread(self, interval, function, args=()):
        thread = threading.Timer(
            interval=float(interval),
            function=function, args=args)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
        return thread

    def create_directory(self, path=''):
        """Create a new directory at the given path."""
        path = self.directory + path
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def remove_directory(self, path):
        """Remove an existing directory at the given path."""
        if os.path.exists(path):
            shutil.rmtree(path)

    def create_progress_bar(self):
        if not self.options.debug:
            return progressbar.PlaybackBar(player=self,
                                           max=self.managed_objects['representations'].duration())
        else:
            return progressbar.NullBar()

    def event(self, action, event):
        self.managed_objects['reporter'].event(action, event)
