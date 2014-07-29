#!/usr/bin/env python2.7

"""Experimental MPEG-DASH request engine with support for accurate logging."""

import collections
import xml.etree.ElementTree as ET
import time
import threading
import Queue
import optparse
import os
import shutil
import requests
import re
import signal
import random
from gauged import Gauged

class Player(object):
    """Object representing scootplayer as a whole."""

    representations = None
    bandwidth = None
    playback_queue = None
    download_queue = None
    reporter = None
    session = None

    def __init__(self):
        """Initialise the player and start playback."""
        self._setup_signal_handling()
        if OPTIONS.playlist:
            playlist = self.parse_playlist(OPTIONS.playlist)
            for manifest in playlist:
                self.play(manifest)
        else:
            self.play(OPTIONS.manifest)

    def play(self, manifest):
        self.representations = None
        self.bandwidth = None
        self.playback_queue = None
        self.download_queue = None
        self.reporter = None
        self.session = None
        self.start_time = time.time()
        self.session = requests.Session()
        time_now = str(int(time.time()))
        self.directory = OPTIONS.output + time_now
        create_directory(self.directory + '/downloads')
        self.reporter = self.Reporter(self)
        self.bandwidth = self.Bandwidth()
        self.representations = self.Representations(self, manifest)
        self.download_queue = self.DownloadQueue(self,
            int(OPTIONS.max_download_queue))
        self.playback_queue = self.PlaybackQueue(self,
            int(self.representations.min_buffer),
            int(OPTIONS.max_playback_queue))
        self.start_playback()

    def parse_playlist(self, path):
        playlist = self.load_playlist(path)
        playlist = re.split(r'(\n)', playlist)
        return self._clean_playlist(playlist)

    def _clean_playlist(self, playlist):
        clean = []
        for item in playlist:
            if len(item) > 2:
                clean.append(item)
        return clean

    def load_playlist(self, path):
        _file = open(path, 'r')
        return _file.read()

    def _setup_signal_handling(self):
        """Setup interrupt signal handling."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGQUIT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle interrupt signals from user."""
        print 'caught signal', str(signum), str(frame)
        print 'stopping scootplayer'
        self.stop()

    def start_playback(self):
        """Start emulated video playback."""
        playback_marker = 0
        duration = 1
        self.reporter.event('start', 'adding representations')
        while True:
            representation = self.representations.candidate(
                int(self.bandwidth))
            try:
                duration = representation[1][playback_marker/duration][0]
                self.download_queue.add(
                    representation[1][playback_marker/duration])
            except IndexError:
                self.reporter.event('stop', 'adding representations')
                #return
            playback_marker += duration

    def make_request(self, item):
        """Make a HTTP request for a single item within the playback queue."""
        url = item[1]
        headers = {}
        if item[3] != 0:
            byte_range = 'bytes=%s-%s' % (item[2], item[3])
            headers['Range'] = byte_range
        response = self.session.get(url, headers=headers)
        if not OPTIONS.keep_alive:
            response.connection.close()
        return response

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

    def stop(self):
        """Stop playback of scootplayer."""
        try:
            self.download_queue.stop()
        except AttributeError:
            pass
        try:
            self.playback_queue.stop()
        except AttributeError:
            pass
        try:
            self.reporter.stop()
        except AttributeError:
            pass
        raise SystemExit()

    class Reporter(object):
        """Object used to report both periodic statistics and events."""

        player = None
        start_time = 0
        report_file = None
        event_file = None
        report = False
        gauged = None

        def __init__(self, player):
            """Initialise files to save reports to."""
            if OPTIONS.gauged:
                self.gauged = Gauged('mysql://root@localhost/gauged')
                self.gauged.sync()
            self.player = player
            file_name = self.player.directory + '/report.csv'
            self.report_file = open(file_name, 'w')
            file_name = self.player.directory + '/event.csv'
            self.event_file = open(file_name, 'w')
            self.start()

        def stop(self):
            """Stop reporting and close file handles."""
            self.report = False
            try:
                self.report_file.close()
            except IOError:
                pass
            try:
                self.event_file.close()
            except IOError:
                pass

        def start(self):
            """Start reporting thread."""
            self.report = True
            self.start_time = time.time()
            thread = threading.Thread(target=self.reporter, args=())
            thread.daemon = True
            thread.start()

        def time_elapsed(self):
            """Calculate the time elapsed since the start of reporting."""
            return round(time.time() - self.start_time, 4)

        def reporter(self):
            """Periodic reporting of various stats (every second) to file."""
            if OPTIONS.gauged:
                try:
                    mean = self.gauged.aggregate('bandwidth', Gauged.MEAN)
                    count = self.gauged.aggregate('downloads', Gauged.SUM)
                    print '[gauged]', mean, count
                except:
                    print '[gauged] exception!'
            if self.report:
                thread = threading.Timer(
                    interval=float(OPTIONS.reporting_period),
                    function=self.reporter, args=())
                thread.daemon = True
                thread.start()
            time_elapsed = self.time_elapsed()
            if OPTIONS.csv:
                try:
                    self.report_file.flush()
                except ValueError:
                    pass
                try:
                    output = (str(time_elapsed) + ","
                     + str(self.player.download_queue.time_buffer) + ","
                     + str(self.player.download_queue.bandwidth) + ","
                     + str(self.player.download_queue.id_) + ","
                     + str(self.player.playback_queue.time_buffer) + ","
                     + str(self.player.playback_queue.time_position) + ","
                     + str(self.player.playback_queue.bandwidth) + ","
                     + str(self.player.playback_queue.id_)  + ","
                     + str(self.player.bandwidth) + "\n")
                except AttributeError:
                    output = str(time_elapsed) + str(', 0, 0, 0, 0, 0, 0, 0\n')
                try:
                    self.report_file.write(output)
                except ValueError:
                    pass
                if OPTIONS.debug:
                    print ("[report] " + output),
                try:
                    self.report_file.flush()
                except ValueError:
                    pass

        def event(self, action, description):
            """Create a thread to handle event."""
            thread = threading.Thread(target=self.event_thread,
                args=(action, description))
            thread.daemon = True
            thread.start()

        def event_thread(self, action, description):
            """Event reporting to file."""
            time_elapsed = self.time_elapsed()
            if OPTIONS.csv:
                try:
                    self.event_file.flush()
                except ValueError:
                    pass
                output = (str(time_elapsed) +  "," + str(action) + ","
                    + str(description) + "\n")
                try:
                    self.event_file.write(output)
                except ValueError:
                    pass
                if OPTIONS.debug:
                    print ("[event] " + output),
                try:
                    self.event_file.flush()
                except ValueError:
                    pass

        def gauged_event(self, **gauged_data):
            """ Create a thread to handle event."""
            if OPTIONS.gauged:
                thread = threading.Thread(target=self.gauged_event_thread,
                    kwargs=gauged_data)
                thread.daemon = True
                thread.start()

        def gauged_event_thread(self, **gauged_data):
            """Event reporting to gauged."""
            try:
                with self.gauged.writer as writer:
                    writer.add(gauged_data)
            except:
                pass

    class Representations(object):
        """
        Object containing the different representations available to the
        player.

        """

        representations = None
        initialisations = None
        min_buffer = 0
        player = None

        def __init__(self, player, manifest):
            """Load the representations from the MPD."""
            self. player = player
            self.representations = list()
            self.initialisations = list()
            self.load_mpd(manifest)
            self.initialise()

        def get_remote_mpd(self, url):
            """Download a remote MPD if necessary."""
            self.player.reporter.event('start', 'fetching remote mpd')
            response = requests.get(url)
            filename = os.path.basename(url)
            path = self.player.directory + '/mpd/'
            create_directory(path)
            _file = open(path + filename, 'w')
            _file.write(response.content)
            self.player.reporter.event('stop', 'fetching remote mpd')
            return path + filename

        def load_mpd(self, manifest):
            """Load an MPD from file."""
            self.player.reporter.event('start', 'parsing mpd')
            expression = r'''http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|
                (?:%[0-9a-fA-F][0-9a-fA-F]))+'''
            url = re.search(expression, manifest)
            if url:
                manifest = self.get_remote_mpd(url.group())
            xml = ET.parse(manifest)
            mpd = xml.getroot()
            base_url = self.BaseURL()
            self.min_buffer = int(float(mpd.attrib['minBufferTime'][2:-1]))
            self.parse_mpd(base_url, mpd)
            sorted(self.representations, key=lambda representation:
                representation[0])
            self.player.reporter.event('stop', 'parsing mpd')

        def parse_mpd(self, base_url, parent_element):
            """Parse 'mpd' level XML."""
            for child_element in parent_element:
                if 'BaseURL' in child_element.tag:
                    base_url.mpd = child_element.text
                self.parse_period(base_url, child_element)
            base_url.mpd = ''

        def parse_period(self, base_url, parent_element):
            """Parse 'period' level XML."""
            for child_element in parent_element:
                if 'BaseURL' in child_element.tag:
                    base_url.period = child_element.text
                self.parse_adaption_set(base_url, child_element)
            base_url.period = ''

        def parse_adaption_set(self, base_url, parent_element):
            """Parse 'adaption set' level XML."""
            for child_element in parent_element:
                if 'BaseURL' in child_element.tag:
                    base_url.adaption_set = child_element.text
                if 'Representation' in child_element.tag:
                    bandwidth = int(child_element.attrib['bandwidth'])
                    try:
                        id_ = int(child_element.attrib['id'])
                    except KeyError:
                        print 'id not found, generating random integer'
                        id_ = random.randint(0, 1000)
                    self.parse_representation(base_url, bandwidth, id_,
                        child_element)
            base_url.adaption_set = ''

        def parse_representation(self, base_url, bandwidth, id_,
            parent_element):
            """Parse 'representation' level XML."""
            for child_element in parent_element:
                if 'SegmentBase' in child_element.tag:
                    self.parse_segment_base(base_url, child_element)
                if 'BaseURL' in child_element.tag:
                    base_url.representation = child_element.text
                if 'SegmentList' in child_element.tag:
                    duration = int(child_element.attrib['duration'])
                    self.parse_segment_list(base_url=base_url,
                        duration=duration, bandwidth=bandwidth, id_=id_,
                        parent_element=child_element)
            base_url.representation = ''

        def parse_segment_base(self, base_url, parent_element):
            """
            Parse 'segment_base' level XML.

            Should be initialisation URLs.

            """
            for child_element in parent_element:
                if 'Initialization' in child_element.tag:
                    try:
                        media_range = child_element.attrib['range'].split('-')
                    except KeyError:
                        media_range = (0, 0)
                    self.initialisations.append((None, base_url.resolve()
                        + child_element.attrib['sourceURL'],
                        int(media_range[0]), int(media_range[1])))

        def parse_segment_list(self, **kwargs):
            """
            Parse 'segment_list' level XML.

            Should be source URLs, describing actual content.

            """
            playlist = list()
            for child_element in kwargs['parent_element']:
                if 'SegmentURL' in child_element.tag:
                    try:
                        media_range = child_element.attrib['mediaRange'] \
                            .split('-')
                    except KeyError:
                        media_range = (0, 0)
                    playlist.append((kwargs['duration'],
                        kwargs['base_url'].resolve()
                        + child_element.attrib['media'], int(media_range[0]),
                        int(media_range[1]), int(kwargs['bandwidth']),
                        int(kwargs['id_'])))
            self.representations.append((kwargs['bandwidth'], playlist))

        def initialise(self):
            """Download necessary initialisation files."""
            self.player.reporter.event('start', 'downloading initializations')
            total_duration = 0
            total_length = 0
            for item in self.initialisations:
                start = time.time()
                response = self.player.make_request(item)
                duration = time.time() - start
                length = float(response.headers.get('Content-Length'))
                length = length * 8 #convert octets to bits
                self.player.write_to_file(item, response)
                self.player.update_bandwidth(duration, length)
                total_duration += duration
                total_length += length
            self.player.update_bandwidth(total_duration, total_length)
            self.player.reporter.event('stop ', 'downloading initializations')

        def candidate(self, bandwidth):
            """
            Select the playback candidate that best matches current bandwidth
            availability.

            """
            candidate_index = min(range(len(self.representations)), key=lambda
                i: abs(self.representations[i][0]-int(bandwidth)))
            return self.representations[candidate_index]

        class BaseURL(object):
            """
            Object used to resolve the current level of base URL.

            This is used as a prefix on the source URL if found.

            """

            representation = None
            adaption_set = None
            period = None
            mpd = None

            def __init__(self):
                """Initialise base URL object by clearing all values."""
                self.clear()

            def clear(self):
                """Clear all values with an empty string."""
                self.representation = ''
                self.adaption_set = ''
                self.period = ''
                self.mpd = ''

            def resolve(self):
                """Return the correct base URL."""
                if self.representation != str(''):
                    return self.representation
                elif self.adaption_set != str(''):
                    return self.adaption_set
                elif self.period != str(''):
                    return self.period
                elif self.mpd != str(''):
                    return self.mpd
                else:
                    return str('')

    class DownloadQueue(object):
        """Object which acts as a download queue for the player."""

        queue = Queue.Queue()
        time_buffer_max = 0
        time_buffer = 0
        player = None
        bandwidth = 0
        id_ = 0

        def __init__(self, player, max_buffer):
            """Initialise download queue with max size and start thread."""
            self.player = player
            self.time_buffer_max = max_buffer
            thread = threading.Thread(target=self.downloader, args=())
            thread.daemon = True
            thread.start()

        def stop(self):
            """Stop the download queue."""
            self.player.reporter.event('final', 'download queue')

        def add(self, representation):
            """Add an item to the download queue."""
            while True:
                if (int(self.time_buffer) + int(representation[0])) \
                    <= int(self.time_buffer_max):
                    self.time_buffer += int(representation[0])
                    self.queue.put((representation))
                    return

        def downloader(self):
            """Download the next item in the download queue."""
            while True:
                item = self.queue.get()
                self.bandwidth = item[4]
                self.id_ = int(item[5])
                start = time.time()
                response = self.player.make_request(item)
                duration = time.time() - start
                length = float(response.headers.get('Content-Length'))
                self.player.write_to_file(item, response)
                self.player.update_bandwidth(duration, length)
                self.player.playback_queue.add(item)
                self.queue.task_done()
                gauged_data = {'downloads':1, 'bandwidth':self.bandwidth,
                    'id_':self.id_, 'length':length}
                self.player.reporter.gauged_event(**gauged_data)
                self.time_buffer = self.time_buffer - int(item[0])

        def __len__(self):
            """Return the current length of the download queue."""
            return self.queue.qsize()

    class PlaybackQueue(object):
        """Object which acts as a playback queue for the player."""

        queue = Queue.Queue()
        bandwidth = 0
        id_ = 0
        time_buffer_min = 0
        time_buffer_max = 0
        time_buffer = 0
        time_position = 0
        start = False
        player = None

        def __init__(self, player, min_buffer, max_buffer):
            """
            Initialise playback queue with minimum and maximum buffer sizes.

            """
            self.player = player
            self.time_buffer_min = min_buffer
            self.time_buffer_max = max_buffer

        def stop(self):
            """Stop the playback queue."""
            self.player.reporter.event('final', 'playback queue')

        def add(self, representation):
            """Add an item to the playback queue."""
            while True:
                if (int(self.time_buffer) + int(representation[0])) \
                 <= int(self.time_buffer_max):
                    self.time_buffer += int(representation[0])
                    self.queue.put((representation))
                    if self.start != True and self.time_buffer  \
                        >= self.time_buffer_min:
                        self.player.reporter.event('start', 'playback')
                        self.start = True
                        thread = threading.Thread(target=self.playback,
                            args=())
                        thread.daemon = True
                        thread.start()
                    return

        def playback(self):
            """Consume the next item in the playback queue."""
            self.time_position = 0
            while self.time_buffer > 0:
                item = self.queue.get()
                self.time_position += int(item[0])
                self.bandwidth = int(item[4])
                self.id_ = int(item[5])
                time.sleep(int(item[0]))
                self.queue.task_done()
                self.time_buffer = self.time_buffer - int(item[0])
            self.player.reporter.event('stop', 'playback')
            self.player.stop()

        def __len__(self):
            """Return the current length of the playback queue."""
            return self.queue.qsize()

    class Bandwidth(object):
        """Object containing the current bandwidth estimation."""

        _current = 0
        _previous = 0
        _trend = collections.deque(maxlen=100)

        def change(self, bandwidth):
            """
            Change the current bandwidth estimation.

            Also records a bandwidth trend (1 for increasing, 0 for the same
            and -1 for decreasing).

            """
            self._previous = self._current
            self._current = bandwidth
            if self._current > self._previous:
                self._trend.append(1)
            elif self._current == self._previous:
                self._trend.append(0)
            elif self._current < self._previous:
                self._trend.append(-1)

        def historical_trend(self):
            """Return the historical trend in bandwidth."""
            return list(self._trend)

        def __str__(self):
            """Returns the current estimated bandwidth."""
            return str(self._current)

        def __int__(self):
            """Returns the current estimated bandwidth."""
            return int(self._current)

def create_directory(path):
    """Create a new directory at the given path."""
    if not os.path.exists(path):
        os.makedirs(path)

def remove_directory(path):
    """Remove an existing directory at the given path."""
    if os.path.exists(path):
        shutil.rmtree(path)

if __name__ == '__main__':
    PARSER = optparse.OptionParser()
    PARSER.set_defaults(output='out/', keep_alive=True,
        max_playback_queue=60, max_download_queue=30, csv=True, gauged=False,
        reporting_period=1, playlist=None, manifest=None)
    PARSER.add_option("-m", "--manifest", dest="manifest",
        help="location of manifest to load")
    PARSER.add_option("-o", "--output", dest="output",
        help="""location to store downloaded files and reports
        [default: %default]""")
    PARSER.add_option("--no-keep-alive", dest="keep_alive",
        action="store_false",
        help="prevent HTTP connection pooling and persistency")
    PARSER.add_option("--max-playback-queue", dest="max_playback_queue",
        help="""set maximum size of playback queue in seconds
        [default: %default seconds]""")
    PARSER.add_option("--max-download-queue", dest="max_download_queue",
        help="""set maximum size of download queue in seconds
        [default: %default seconds]""")
    PARSER.add_option("-d", "--debug", dest="debug", action="store_true",
        help="print all output to console")
    PARSER.add_option("-r", "--reporting-period", dest="reporting_period",
        help="set reporting period in seconds")
    PARSER.add_option("--no-csv", dest="csv",
        action="store_false",
        help="stop CSV writing")
    PARSER.add_option("-g", "--gauged", dest="gauged",
        action="store_true",
        help="experimental gauged support")
    PARSER.add_option("-p", "--playlist", dest="playlist",
        help="playlist of MPDs to play in succession")
    (OPTIONS, ARGS) = PARSER.parse_args()
    if (OPTIONS.manifest != None or OPTIONS.playlist != None) and not (
        OPTIONS.manifest and OPTIONS.playlist):
        try:
            PLAYER = Player()
        except SystemExit:
            raise
    else:
        PARSER.print_help()
