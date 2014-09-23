#!/usr/bin/env python2.7

"""Experimental MPEG-DASH request engine with support for accurate logging."""

import time
import Queue
import optparse
import os
import signal
import shutil
import requests
import threading
from progress.bar import Bar

import scootplayer.remote as remote
import scootplayer.reporter as reporter
import scootplayer.watchdog as watchdog
import scootplayer.representations as representations
import scootplayer.bandwidth as bandwidth
import scootplayer.queue as queue

class Scootplayer(object):
    """Object representing scootplayer as a whole."""

    session = None
    bandwidth = None

    managed_objects = {'download': None,
                       'playback': None,
                       'download': None,
                       'playlist': None,
                       'representations': None,
                       'reporter': None,
                       'watchdog': None,
                       'remote_control': None}

    threads = list()

    def __init__(self, options):
        """Initialise the player and start playback."""
        self.options = options
        self._setup_signal_handling()
        self.managed_objects['watchdog'] = watchdog.Watchdog(self)
        self.managed_objects['remote_control'] = remote.RemoteControl(self, options)
        self.managed_objects['playlist'] = queue.playlist.PlaylistQueue(self, options)
        self.next()
        self._consumer()

    def next(self):
        self._init_reporter()
        self.pause()
        self.session = requests.Session()
        self.bandwidth = bandwidth.Bandwidth()
        manifest = self.managed_objects['playlist'].get()
        self.managed_objects['representations'] = representations.Representations(self, manifest)
        self.bar = self.create_progress_bar()
        self.managed_objects['download'] = queue.download.DownloadQueue(player=self,
            time_buffer_max=int(self.options.max_download_queue))
        self.managed_objects['playback'] = queue.playback.PlaybackQueue(player=self,
            time_buffer_min=int(self.managed_objects['representations'].min_buffer),
            time_buffer_max=int(self.options.max_playback_queue))
        self.resume()

    def _init_reporter(self):
        time_now = str(int(time.time()))
        self.directory = self.options.output + time_now
        self.create_directory(self.directory + '/downloads')
        self.managed_objects['reporter'] = reporter.Reporter(self)

    def _consumer(self):
        while True:
            self.bar.next(0)
            if self.state == 'play':
                try:
                    representation = self.managed_objects['representations'] \
                        .candidate(int(self.bandwidth))
                    self.managed_objects['download'].add(representation)
                except Queue.Empty:
                    self.next()
            else:
                time.sleep(10)

    def exit(self):
        self.state = 'exit'
        self.stop()
        raise SystemExit()

    def pause(self):
        self.state = 'pause'
        self._modify_state(False)

    def resume(self):
        self.state = 'play'
        self._modify_state(True)

    def stop(self):
        """Stop playback of scootplayer."""
        self.state = 'stop'
        self.bar.suffix = '0:00 / 0:00 / stop'
        self.bar.next(0)
        self._modify_state('stop')

    def _modify_state(self, state=None):
        for _, val in self.managed_objects.items():
            try:
                if type(state) is bool:
                    val.__dict__['run'] = state
                else:
                    getattr(val, state)()
            except AttributeError:
                pass

    def _setup_signal_handling(self):
        """Setup interrupt signal handling."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle interrupt signals from user."""
        print 'caught signal', str(signum), str(frame)
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
        for object_ in ['download', 'playback']:
            for key, val in self.managed_objects[object_].__dict__[metric].items():
                result[object_ + '_' + key] = val
        return result

    def max_duration(self):
        return self.managed_objects['representations'].max_duration

    def analysis(self):
        try:
            self.managed_objects['playback'].bandwidth_analysis()
            self.managed_objects['playback'].queue_analysis()
            self.managed_objects['download'].queue_analysis()
        except AttributeError:
                pass #Download and playback queues not yet initialised


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

    def create_directory(self, path):
        """Create a new directory at the given path."""
        if not os.path.exists(path):
            os.makedirs(path)

    def remove_directory(self, path):
        """Remove an existing directory at the given path."""
        if os.path.exists(path):
            shutil.rmtree(path)

    def create_progress_bar(self):
        if not self.options.debug:
            return self.PlaybackBar(player=self, max=self.managed_objects['representations'].duration())
        else:
            return self.EmptyBar()

    def event(self, action, event):
        self.managed_objects['reporter'].event(action, event)

    class EmptyBar():

        def next(self, _):
            pass

    class PlaybackBar(Bar):

        def __init__(self, *args, **kwargs):
            super(Bar, self).__init__(*args, **kwargs)
            total = "%02d:%02d" % (divmod(self.max, 60))
            self.suffix = '%(elapsed)s / ' + total + ' / ' + '%(state)s'

        @property
        def elapsed(self):
            return "%02d:%02d" % (divmod(self.index, 60))

        @property
        def state(self):
            return self.player.state

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.set_defaults(output='out/', keep_alive=True,
        max_playback_queue=60, max_download_queue=30, csv=True, gauged=False,
        reporting_period=1, playlist=None, manifest=None, xml_validation=False,
        remote_control_host='localhost', remote_control_port='5556')
    parser.add_option("-m", "--manifest", dest="manifest",
        help="location of manifest to load")
    parser.add_option("-o", "--output", dest="output",
        help="""location to store downloaded files and reports
        [default: %default]""")
    parser.add_option("--no-keep-alive", dest="keep_alive",
        action="store_false",
        help="prevent HTTP connection pooling and persistency")
    parser.add_option("--max-playback-queue", dest="max_playback_queue",
        help="""set maximum size of playback queue in seconds
        [default: %default seconds]""")
    parser.add_option("--max-download-queue", dest="max_download_queue",
        help="""set maximum size of download queue in seconds
        [default: %default seconds]""")
    parser.add_option("-d", "-v", "--debug", "--verbose", dest="debug", action="store_true",
        help="print all output to console")
    parser.add_option("-r", "--reporting-period", dest="reporting_period",
        help="set reporting period in seconds")
    parser.add_option("--no-csv", dest="csv",
        action="store_false",
        help="stop CSV writing")
    parser.add_option("-g", "--gauged", dest="gauged",
        action="store_true",
        help="experimental gauged support")
    parser.add_option("-p", "--playlist", dest="playlist",
        help="playlist of MPDs to play in succession")
    parser.add_option("-x", "--xml-validation", dest="xml_validation",
        action="store_true",
        help="validate the MPD against the MPEG-DASH schema")
    parser.add_option("-c", "--remote-control-host", dest="remote_control_host",
        help="""set hostname of the remote controller to listen to
        [default: %default]""")
    parser.add_option("--remote-control-port", dest="remote_control_port",
        help="""set port of the remote controller to listen to
        [default: %default]""")
    (options, argsn) = parser.parse_args()
    if (options.manifest != None or options.playlist != None) and not (
        options.manifest and options.playlist) or options.remote_control_host:
        try:
            PLAYER = Scootplayer(options)
        except SystemExit:
            raise
    else:
        parser.print_help()
