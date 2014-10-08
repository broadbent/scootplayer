#!/usr/bin/env python2.7

"""Represents the different playback levels in an MPD."""

from lxml import etree
import aniso8601
import os
import Queue
import random
import re
import requests
from pymediainfo import MediaInfo


class Representations(object):

    """
    Parses an MPD and contains the representations available to the
    player. Also decides the most appropriate candidate given a bandwidth.

    """

    media = {'representations': None, 'initialisations': None}
    representations = None
    initialisations = None
    min_buffer = 0
    max_duration = 0
    max_bandwidth = 0
    first_chunk = True
    player = None
    duration = 0

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
        response = requests.get(url)
        filename = os.path.basename(url)
        path = self.player.create_directory('/mpd')
        _file = open(path + filename, 'w')
        _file.write(response.content)
        self.player.event('stop', 'fetching remote mpd')
        return path + filename

    def load_mpd(self, manifest):
        """Load an MPD from file."""
        self.player.event('start', 'parsing mpd')
        expression = r'''http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|
            (?:%[0-9a-fA-F][0-9a-fA-F]))+'''
        url = re.search(expression, manifest)
        if url:
            manifest = self._get_remote_mpd(url.group())
        if self.player.options.xml_validation:
            document = self._validate_mpd(manifest)
        else:
            document = etree.parse(manifest)
        mpd = document.getroot()
        base_url = self.BaseURL()
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
            self._set_duration(parent_element.get('mediaPresentationDuration'))
        except (TypeError, IndexError, ValueError):
            self.duration = 0
        for child_element in parent_element:
            if 'BaseURL' in child_element.tag:
                base_url.mpd = child_element.text
            self.parse_period(base_url, child_element)
        base_url.mpd = ''

    def _set_duration(self, duration):
        """Set the duration of playback defined in the MPD."""
        self.duration = aniso8601.parse_duration(duration).seconds

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

    def parse_representation(self, base_url, bandwidth, id_, parent_element):
        """Parse 'representation' level XML."""
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
        if duration > self.max_duration:
            self.max_duration = duration
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
                self.media['initialisations'].append((None, base_url.resolve() +
                                                      child_element.attrib[
                                                          'sourceURL'],
                                                      int(media_range[0]),
                                                      int(media_range[1]),
                                                      bandwidth, id_))

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
                queue.put((kwargs['duration'],
                           kwargs['base_url'].resolve() +
                           child_element.attrib['media'], int(media_range[0]),
                           int(media_range[1]), int(kwargs['bandwidth']),
                           int(kwargs['id_'])))
        self.media['representations'].append({
            'bandwidth': kwargs['bandwidth'],
            'id': kwargs['id_'], 'queue': queue,
            'maximum_encoded_bitrate': 0})

    def initialise(self):
        """Download necessary initialisation files."""
        self.player.event('start', 'downloading initializations')
        self.player.create_directory('/downloads')
        total_duration = 0
        total_length = 0
        if self.player.options.vlc:
            for item in self.media['initialisations']:
                if item[4] == self.max_bandwidth:
                    total_duration, total_length, path = self.player.fetch_item(
                        item)
                else:
                    self.player.fetch_item(item, dummy=True)
        else:
            for item in self.media['initialisations']:
                duration, length, path = self.player.fetch_item(item)
                total_duration += duration
                total_length += length
                self._parse_metadata(path, item[5])
        self.player.update_bandwidth(total_duration, total_length)
        self.player.event('stop ', 'downloading initializations')

    def _parse_metadata(self, path, id_):
        """
        Parse the MP4 header metadata for bitrate information.

        Specifically, retrieve the maximum encoded bitrate for each quality
        level.

        """
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
                candidate = {'item': representation['queue'].get(),
                             'id': representation['id'],
                             'bandwidth': representation['bandwidth'],
                             'max_encoded_bitrate':
                             representation['maximum_encoded_bitrate']}
            else:
                representation['queue'].get()
        if candidate is None:
            raise Queue.Empty
        return candidate

    def bandwidth_match(self, bandwidth):
        """Matches the bandwidth with the nearest representation."""
        candidate_index = min(range(len(self.media['representations'])),
                              key=lambda
                              i: abs(self.media['representations']
                                     [i]['bandwidth'] - int(bandwidth)))
        return candidate_index

    class BaseURL(object):

        """
        Used to resolve the current level of base URL.

        Determines a prefix on the source URL if found.

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
