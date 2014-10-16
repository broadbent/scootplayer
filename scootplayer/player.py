#!/usr/bin/env python2.7

"""Experimental MPEG-DASH player emulator."""

import os
import requests
import shutil
import signal
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

    """Main player which facilitates interaction between the other modules."""
    bandwidth = None
    managed_objects = {'download': None,
                       'playback': None,
                       'playlist': None,
                       'representations': None,
                       'reporter': None,
                       'watchdog': None,
                       'remote_control': None}
    session = None
    threads = list()
    finished = False
    progress_bar = None
    state = 'stop'
    directory = ''
    current_manifest = ''

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
        if self.managed_objects['playlist'].empty():
            self.event('empty', 'playlist')
            self.exit()
        self.finished = False
        self._directory_setup()
        self.managed_objects['reporter'] = reporter.Reporter(self)
        self.event('next', 'playing next item')
        self.pause()
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=int(self.options.conn_pool),
            pool_maxsize=int(self.options.conn_pool))
        self.session.mount('http://', adapter)
        self.bandwidth = bandwidth.Bandwidth()
        self.current_manifest = self.managed_objects['playlist'].get()
        self.managed_objects['representations'] = \
            representations.Representations(self, self.current_manifest)
        window_size = self.max_duration() * int(self.options.window_multiplier)
        self.managed_objects['download'] = queue.download.DownloadQueue(
            player=self, time_buffer_max=int(self.options.max_download_queue),
            window_size=window_size)
        self.managed_objects['playback'] = queue.playback.PlaybackQueue(
            player=self, time_buffer_min=int(
                self.managed_objects['representations'].min_buffer),
            time_buffer_max=int(self.options.max_playback_queue),
            window_size=window_size)
        self.progress_bar = self._create_progress_bar()
        self.managed_objects['watchdog'] = watchdog.Watchdog(self)
        self._setup_scheduled_stop(self.options.playback_time)
        self.resume()

    def _directory_setup(self):
        """Create directory for storing downloads"""
        time_now = str(int(time.time()))
        self.directory = '/'.join(__file__.split('/')
                                  [:-2]) + '/' + self.options.output + \
            '/' + time_now
        self.create_directory()

    def _consumer(self):
        """
        Fetch a representation matching the current bandwidth. Add this to the
        download queue.

        If the player is not playing, wait for a second before
        checking again if the playback is resumed.
        """
        while True:
            self.progress_bar.next(0)
            if self.state == 'play':
                representation = self.managed_objects['representations'] \
                    .candidate(int(self.bandwidth))
                self.managed_objects['download'].add(representation)
                if self.finished:
                    self.next()
            else:
                time.sleep(0.01)

    def _setup_scheduled_stop(self, time_):
        """
        If defined in the configuration options, stop the player at a
        predetermined time.

        """
        if time_:
            self.start_timed_thread(time_, self.exit)

    def finish_playback(self):
        """Mark playback as finished when method called."""
        self.finished = True

    def exit(self):
        """Stop playback and exit player."""
        self.state = 'exit'
        self.stop()
        os._exit(0)  # TODO: No cleanup on exit
        # sys.exit(0)

    def pause(self):
        """Pause playback."""
        self.state = 'pause'
        self._modify_state('pause')

    def resume(self):
        """Resume playback."""
        self.state = 'play'
        self._modify_state('resume')

    def stop(self):
        """Stop playback."""
        self.state = 'stop'
        self.progress_bar.suffix = '0:00 / 0:00 / stop'
        self.progress_bar.next(0)
        self._modify_state('stop')

    def _modify_state(self, method=None):
        """Call given method on each of the managed objects."""
        for _, val in self.managed_objects.items():
            try:
                getattr(val, method)()
            except AttributeError:
                pass

    def _setup_signal_handling(self):
        """Setup interrupt signal handling."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGQUIT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals from user."""
        self.exit()

    def make_request(self, item):
        """Make a HTTP request for a single item within the playback queue."""
        url = item['url']
        headers = {}
        if item['bytes_to'] != 0:
            byte_range = 'bytes=%s-%s' % (item['bytes_from'], item['bytes_to'])
            headers['Range'] = byte_range
        try:
            response = self.session.get(url, headers=headers)
        except requests.exceptions.ConnectionError:
            response = None  # Return a None value if connection has failed.
        if not self.options.keep_alive:
            response.connection.close()
        return response

    def open_file(self, path):
        """Open a file and return the file handle."""
        file_name = self.directory + path
        return open(file_name, 'w')

    def fetch_item(self, item, dummy=False):
        """
        Fetch an individual item from a remote location.

        Writes the item to file. Also updates the bandwidth based upon the
        duration of the transaction and the amount of bits received in that
        time.

        Returns:
            duration: time taken to fulfil the request
            length: response length for use with the MPD '@bandwidth' value
                (in bits).
        """
        if not dummy:
            self.event('start', 'downloading ' + str(item['url']))
            response, duration = self._time_request(item)
            self._check_code(response.status_code, item['url'])
            length = get_length(response)
            path = self._write_to_file(item, response.content)
            self.update_bandwidth(duration, length)
            self.event('stop', 'downloading ' + str(item['url']) +
                       ' (' + str(length) + 'b)')
            return duration, length, path
        else:
            path = self._write_to_file(item, '')
            return 0, 0, path

    def item_ready(self, item):
        """Add a given item to the playback queue."""
        self.managed_objects['playback'].add(item)

    def retrieve_metric(self, metric, func=None):
        """Retrieve given metric from each of the managed objects."""
        if func:
            self._modify_state(func)
        result = {}
        for obj in ['download', 'playback']:
            result[obj] = self.managed_objects[obj].__dict__[metric]
        return result

    def max_duration(self):
        """Return maximum duration present in current set of representations."""
        return self.managed_objects['representations'].max_duration

    def report_tick(self):
        """Call report method on each of the managed objects."""
        self._modify_state('report_tick')

    def _time_request(self, item):
        """Make request and time response."""
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

    def _write_to_file(self, item, content):
        """
        Write response content to file.

        This may be a complete file, or a byte range to an existing file.

        """
        file_name = item['url'].split('/')[-1]
        path = self.directory + '/downloads/' + file_name
        file_start = int(item['bytes_from'])
        file_end = int(item['bytes_to'])
        try:
            _file = open(path, 'r+')
        except IOError:
            _file = open(path, 'w')
        _file.seek(int(item['bytes_from']))
        _file.write(content)
        file_pointer = int(_file.tell() - 1)
        if file_end != file_pointer and file_start != 0:
            print 'ends do not match'
        _file.close()
        return path

    def update_bandwidth(self, duration, length):
        """Update the current bandwidth estimation."""
        if duration == 0 or length == 0:
            pass
        else:
            self.bandwidth.change(int(length / duration))

    def start_thread(self, target, args=(), **kwargs):
        """Wrapper for the `threading.Thread` module. Track threads."""
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
        return thread

    def start_timed_thread(self, interval, function, args=()):
        """Wrapper for the `threading.Timer` module. Track threads."""
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

    def _create_progress_bar(self):
        """Create a progress bar if required."""
        if not self.options.debug:
            return progressbar.PlaybackBar(player=self,
                                           max=self
                                           .managed_objects['representations']
                                           .duration)
        else:
            return progressbar.NullBar()

    def event(self, action, event):
        """Register event with the reporting module."""
        try:
            self.managed_objects['reporter'].event(action, event)
        except AttributeError:
            print action, event

def get_length(response):
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


def remove_directory(path):
    """Remove an existing directory at the given path."""
    if os.path.exists(path):
        shutil.rmtree(path)
