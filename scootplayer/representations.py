#!/usr/bin/env python2.7

"""Represents the different playback levels in an MPD."""

from lxml import etree
import aniso8601
import os
import Queue
import random
import re
import requests
import threading
import time
import multiprocessing
from pymediainfo import MediaInfo


def call_it(instance, name, args=(), kwargs=None):
    "Indirect caller for instance methods and multiprocessing."
    if kwargs is None:
        kwargs = {}
    return getattr(instance, name)(*args, **kwargs)


class Representations(object):
    """
    Parses an MPD and contains the representations available to the
    player. Also decides the most appropriate candidate given a bandwidth.

    """

    media = {'representations': None, 'initialisations': None}
    representations = None
    initialisations = None
    min_buffer = 0
    max_seg_duration = 0
    max_bandwidth = 0
    first_chunk = True
    player = None
    mpd_duration = 0
    init_done = 0
    total_duration = 0
    total_length = 0

    def __init__(self, player, manifest):
        """Load the representations from the MPD."""
        self.player = player
        self.media['representations'] = list()
        self.media['initialisations'] = list()
        self.load_mpd(manifest)
        self.initialise()

    def stop(self):
        """Clear the current set of representations and initialisations."""
        self.media['representations'] = list()
        self.media['initialisations'] = list()
        self.player.event('stop', 'representations')

    def _get_remote_mpd(self, url):
        """Download a remote MPD if necessary."""
        self.player.event('start', 'fetching remote mpd')
        try:
            response = requests.get(url)
        except requests.ConnectionError as exception:
            self.player.event('error', str(exception))
            return ''
        filename = os.path.basename(url)
        path = self.player.create_directory('/downloads/mpd') + '/' + filename
        _file = open(path, 'w')
        _file.write(response.content)
        self.player.event('stop', 'fetching remote mpd')
        return path

    def load_mpd(self, manifest):
        """Load an MPD from file."""
        self.player.event('start', 'parsing mpd: ' + str(manifest))
        pattern = r'''http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|
            (?:%[0-9a-fA-F][0-9a-fA-F]))+'''
        url = re.search(pattern, manifest)
        if url:
            manifest = self._get_remote_mpd(url.group())
            origin = '/'.join(url.group().split('/')[:-1]) + '/'
        else:
            origin = ''
        if self.player.options.xml_validation:
            document = self._validate_mpd(manifest)
        else:
            document = etree.parse(manifest)
        mpd = document.getroot()
        base_url = self.BaseURL(origin)
        self.min_buffer = int(float(mpd.attrib['minBufferTime'][2:-1]))
        self.parse_mpd(base_url, mpd)
        sorted(self.media['representations'], key=lambda representation:
               representation['bandwidth'])
        self.player.event('stop', 'parsing mpd')

    def _validate_mpd(self, manifest):
        """Validate the integrity of the schema and MPD."""
        schema = open('validation/DASH-MPD.xsd')
        schema = etree.parse(schema)
        self.player.event('start', 'validating schema')
        try:
            schema = etree.XMLSchema(schema)
        except etree.XMLSchemaParseError as exception:
            self.player.event('error', str(exception))
            raise SystemExit()
        self.player.event('stop', 'validating schema')
        try:
            document = etree.parse(manifest)
        except etree.XMLSyntaxError as exception:
            self.player.event('error', str(exception))
            raise SystemExit()
        self.player.event('start', 'validating document')
        try:
            schema.assertValid(document)
        except etree.DocumentInvalid as exception:
            self.player.event('error', str(exception))
            raise SystemExit()
        self.player.event('stop', 'validating document')
        return document

    def parse_mpd(self, base_url, parent_element):
        """Parse 'mpd' level XML."""
        try:
            self._set_mpd_duration(
                parent_element.get('mediaPresentationDuration'))
        except (TypeError, IndexError, ValueError):
            self.mpd_duration = 0
        for child_element in parent_element:
            if 'BaseURL' in child_element.tag:
                base_url.mpd = child_element.text
            if 'Period' in child_element.tag:
                self.parse_period(base_url, child_element)
        base_url.mpd = ''

    def _set_mpd_duration(self, duration):
        """Set the duration of playback defined in the MPD."""
        self.mpd_duration = aniso8601.parse_duration(duration).seconds

    def parse_period(self, base_url, parent_element):
        """Parse 'period' level XML."""
        for child_element in parent_element:
            if 'BaseURL' in child_element.tag:
                base_url.period = child_element.text
            if 'AdaptationSet' in child_element.tag:
                self.parse_adaptation_set(base_url, child_element)
        base_url.period = ''

    def parse_adaptation_set(self, base_url, parent_element):
        """Parse 'adaption set' level XML. Create a new template if present."""
        template = None
        for child_element in parent_element:
            if 'BaseURL' in child_element.tag:
                base_url.adaption_set = child_element.text
            if 'SegmentTemplate' in child_element.tag:
                template = self.Template(child_element)
            elif 'Representation' in child_element.tag:
                bandwidth = int(child_element.attrib['bandwidth'])
                try:
                    id_ = str(child_element.attrib['id'])
                except KeyError:
                    print 'id not found, generating random number'
                    id_ = str(random.randint(0, 1000))
                if template:
                    self.parse_templated_representation(template, base_url, child_element)
                else:
                    self.parse_representation(base_url, bandwidth, id_,
                                          child_element)
        base_url.adaption_set = ''

    def parse_templated_representation(self, template, base_url, parent_element):
         """Parse 'representation' level XML given a template."""
         bandwidth = int(parent_element.attrib['bandwidth'])
         duration = template.duration / template.timescale
         total_files = (self.mpd_duration / duration)  + 1
         self._max_values(duration, bandwidth)
         queue = Queue.Queue()
         for number in range(template.start_number, total_files + 1):
             media = template.resolve(representationID=str(parent_element.attrib['id']),
                number=number, bandwidth=bandwidth, time=(number * duration))
             queue.put({'duration': duration, 'url': base_url.resolve() + media,
             'bytes_from': int(0),
             'bytes_to': int(0)})
         self.media['representations'].append({
             'bandwidth': bandwidth,
             'id': str(parent_element.attrib['id']), 'queue': queue,
             'maximum_encoded_bitrate': 0})

    def parse_representation(self, base_url, bandwidth, id_, parent_element):
        """Parse 'representation' level XML without a template."""
        for child_element in parent_element:
            if 'SegmentBase' in child_element.tag:
                self.parse_segment_base(
                    base_url,
                    bandwidth,
                    id_,
                    child_element)
            if 'BaseURL' in child_element.tag:
                base_url.representation = child_element.text
            if 'SegmentList' in child_element.tag:
                duration = int(child_element.attrib['duration'])
                self._max_values(duration, bandwidth)
                self.parse_segment_list(base_url=base_url,
                                        duration=duration,
                                        bandwidth=bandwidth,
                                        id_=id_,
                                        parent_element=child_element)
        base_url.representation = ''

    def _max_values(self, duration, bandwidth):
        """Find maximum values for duration and bandwidth in the MPD."""
        if duration > self.max_seg_duration:
            self.max_seg_duration = duration
        if bandwidth > self.max_bandwidth:
            self.max_bandwidth = bandwidth

    def parse_segment_base(self, base_url, bandwidth, id_, parent_element):
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
                self.media['initialisations'].append({
                           'bandwidth' : bandwidth,
                           'id' : id_,
                           'item': {'duration': 0,
                                    'url': base_url.resolve() +
                                    child_element.attrib['sourceURL'],
                                    'bytes_from': int(media_range[0]),
                                    'bytes_to': int(media_range[1])}
                                    })

    def parse_segment_list(self, **kwargs):
        """
        Parse 'segment_list' level XML.

        Should be source URLs, describing actual content.

        """
        queue = Queue.Queue()
        for child_element in kwargs['parent_element']:
            if 'SegmentURL' in child_element.tag:
                try:
                    media_range = child_element.attrib['mediaRange'] \
                        .split('-')
                except KeyError:
                    media_range = (0, 0)
                queue.put({'duration': kwargs['duration'],
                           'url': kwargs['base_url'].resolve() +
                           child_element.attrib['media'],
                           'bytes_from': int(media_range[0]),
                           'bytes_to': int(media_range[1])})
        self.media['representations'].append({
            'bandwidth': kwargs['bandwidth'],
            'id': kwargs['id_'], 'queue': queue,
            'maximum_encoded_bitrate': 0})

    def initialise(self):
        """
        Fetch the necessary initialisation files.

        If there are multiple initialisation files to download, this will be
        done concurrently.

        """
        self.player.event('start', 'downloading initializations')
        if self.player.options.write:
            self.player.create_directory('/downloads')
        elif self.player.options.vlc:
            for init in self.media['initialisations']:
                if init['bandwidth'] == self.max_bandwidth:
                    total_duration, total_length, _ = self.player.fetch_item(init['item'])
                else:
                    self.player.fetch_item(init['item'], dummy=True)
        if self.player.options.threading:
            self._multithreaded_fetch()
        else:
            self._multiprocessing_fetch()
        self.player.update_bandwidth(self.total_duration, self.total_length)
        self.player.event('stop ', 'downloading initializations')

    def _multithreaded_fetch(self):
        self.done = 0
        lock = threading.Lock()
        for item in self.media['initialisations']:
            self.player.start_thread(self.fetch_initialisation,
                                     (item, lock))
        while self.init_done < len(self.media['initialisations']):
            time.sleep(0.01)

    def _multiprocessing_fetch(self):
        pool = multiprocessing.Pool(
            processes=int(self.player.options.proc_pool))
        results = [pool.apply_async(call_it,
                   args=(self, 'fetch_initialisation', (item,)))
                   for item in self.media['initialisations']]
        pool.close()
        map(multiprocessing.pool.ApplyResult.wait, results)
        for result in results:
            duration, length, _ = result.get()
            self.total_duration += duration
            self.total_length += length

    def fetch_initialisation(self, initialisation, lock=None):
        """
        Fetch an initialisation and update the shared duration and length
        totals.

        Delay the parsing of header metadata for a few seconds to allow
        playback to start.

        """
        duration, length, path = self.player.fetch_item(initialisation['item'])
        if lock:
            lock.acquire()
            try:
                self.total_duration += duration
                self.total_length += length
                self.init_done += 1
            finally:
                lock.release()
        self.player.start_timed_thread(10, self.parse_metadata, (path,
                                       initialisation['id']))
        return duration, length, path

    def parse_metadata(self, path, id_):
        """
        Parse the MP4 header metadata for bitrate information.

        Specifically, retrieve the maximum encoded bitrate for each quality
        level.

        """
        self.player.event('start', 'parsing metadata ' + str(path))
        found = False
        try:
            media_info = MediaInfo.parse(path)
        except OSError:
            self._set_maximum_encoded_bitrate(0, id_)
            self.player.event('error', 'MediaInfo not installed')
            return
        for track in media_info.tracks:
            if track.track_type == 'Video':
                maximum_bitrate = track.maximum_bit_rate
                if maximum_bitrate:
                    self._set_maximum_encoded_bitrate(maximum_bitrate, id_)
                    found = True
                else:
                    self.player.event(
                        'error',
                        'maximum bitrate not found in metadata')
                    self._set_maximum_encoded_bitrate(0, id_)
                    return
        if not found:
            self.player.event('error', 'no video track in metadata')
            self._set_maximum_encoded_bitrate(0, id_)
        self.player.event('stop', 'parsing metadata ' + str(path))

    def _set_maximum_encoded_bitrate(self, bitrate, id_):
        """
        Includes the maximum encoded bitrate in the data for each representaton.

        """
        representation = (
            i for i in self.media['representations'] if i['id'] == id_).next()
        representation['maximum_encoded_bitrate'] = bitrate

    def candidate(self, bandwidth):
        """
        Select the playback candidate that best matches current bandwidth
        availability.

        """
        # TODO: account for none aligned segments
        if self.player.options.vlc and self.first_chunk:
            candidate_index = self.bandwidth_match(self.max_bandwidth)
            self.first_chunk = False
        else:
            candidate_index = self.bandwidth_match(bandwidth)
        candidate = None
        for representation in self.media['representations']:
            if representation is self.media[
                    'representations'][candidate_index]:
                try:
                    candidate = {'item': representation['queue'].get_nowait(),
                                 'id': representation['id'],
                                 'bandwidth': representation['bandwidth'],
                                 'max_encoded_bitrate':
                                 representation['maximum_encoded_bitrate']}
                except Queue.Empty:
                    break
            else:
                try:
                    representation['queue'].get_nowait()
                except Queue.Empty:
                    break
        return candidate

    def bandwidth_match(self, bandwidth):
        """Matches the bandwidth with the nearest representation."""
        candidate_index = min(range(len(self.media['representations'])),
                              key=lambda
                              i: abs(self.media['representations']
                                     [i]['bandwidth'] - int(bandwidth)))
        return candidate_index

    class Template(object):

        """
        Represents a Segment Template and the details within.

        Used to resolve a URL given the current parameters.

        """

        def __init__(self, element):
            """Initialise template object using XML element."""
            self.timescale = int(element.attrib['timescale'])
            self.media = str(element.attrib['media'])
            self.start_number = int(element.attrib['startNumber'])
            self.duration = int(element.attrib['duration'])
            self.initialisation = str(element.attrib['initialization'])

        def resolve(self, **kwargs):
            """Return the URL with arguments substituted."""
            media = self.media
            for key, value in kwargs.items():
                key = "$" + key.title() +"$"
                media = media.replace(key, str(value))
            return media

    class BaseURL(object):

        """
        Used to resolve the current level of base URL.

        Determines a prefix on the source URL if found.

        """

        representation = None
        adaption_set = None
        period = None
        mpd = None
        origin = None

        def __init__(self, origin):
            """Initialise base URL object by clearing all values."""
            self.clear()
            self.origin = origin

        def clear(self):
            """Clear all values with an empty string."""
            self.representation = ''
            self.adaption_set = ''
            self.period = ''
            self.mpd = ''
            self.origin = ''

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
                return self.origin
