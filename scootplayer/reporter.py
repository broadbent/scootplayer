#!/usr/bin/env python2.7

"""Reporter used to report periodic statistics and events."""

import time
import platform
import sys


class Reporter(object):

    """
    Handles the reporting of player statistics and events to STDOUT and file.
    """

    player = None
    start_time = 0
    report_file = None
    event_file = None
    stats_file = None
    report = False
    options = None
    run = False
    startup_delay = 0
    csv_new = True
    managed_files = {}
    _object_focus = ['playback', 'download']
    _header_width = 0

    def __init__(self, player):
        """Initialise files to save reports to."""
        self.player = player
        self._setup_managed_files()
        self.start_time = time.time()
        self.player.start_timed_thread(5, self.info)
        self.start()

    def info(self):
        """Collect system and Python information to aid with profiling."""
        self.managed_files['info'] = self.player.open_file('/info.csv')
        self.managed_files['info'].write('local time,' +
                                         time.strftime("%d/%m/%Y %H:%M:%S",
                                         time.localtime(self.start_time))
                                         + '\n')
        self.managed_files['info'].write('manifest,' +
                                         self.player.current_manifest + '\n')
        self.managed_files['info'].write('python version,'
                                         + str(sys.version_info.major)
                                         + '.' + str(sys.version_info.minor)
                                         + '.' + str(sys.version_info.micro)
                                         + '\n')
        self.managed_files['info'].write('system platform,' + platform.system()
                                         + '\n')
        self.managed_files['info'].write('system node,' + platform.node()
                                         + '\n')
        self.managed_files['info'].write('system release,' + platform.release()
                                         + '\n')
        self.managed_files['info'].write('system version,' + platform.version()
                                         + '\n')
        self.managed_files['info'].write('system machine,' + platform.machine()
                                         + '\n')
        self.managed_files['info'].write('system processor,'
                                         + platform.processor() + '\n')
        self.managed_files['info'].flush()

    def _setup_managed_files(self):
        """Setup the files required at playback start."""
        self.managed_files['event'] = self.player.open_file('/event.csv')
        self._create_dir_structure('report', self._object_focus)

    def _create_dir_structure(self, folder, files):
        """Create a folder containing a number of (empty) CSV files."""
        self.player.create_directory(path='/' + folder)
        for file in files:
            self.managed_files[folder + '_' + file] = self.player.open_file(
                '/' + folder + '/' + file + '.csv')

    def stop(self):
        """Stop reporting and close file handles."""
        self.run = False
        self._stats()
        for _, obj in self.managed_files.items():
            try:
                getattr(obj, 'close')()
            except AttributeError:
                pass
        self.player.event('stop', 'reporter')

    def pause(self):
        """Pause the reporting."""
        self.run = False

    def resume(self):
        """Resume the reporting."""
        self.run = True

    def start(self):
        """Start reporting thread."""
        self.csv_new = True
        self.player.start_thread(self.reporter)

    def time_elapsed(self):
        """Calculate the time elapsed since the start of reporting."""
        return round(time.time() - self.start_time, 4)

    def reporter(self):
        """
        Periodic reporting of various stats (every second) to file.

        If CSV file is new, append headers to first row.

        """
        self.player.start_timed_thread(self.player.options.reporting_period,
                                       self.reporter)
        if self.run:
            self.player.report_tick()
            if self.player.options.csv:
                if self.csv_new:
                    self._csv_setup()
                self.csv_report()

    def _stats(self):
        """Retrieve statistics and print them to file."""
        self._create_dir_structure('stats', self._object_focus)
        stats = self.player.retrieve_metric('stats', func='calculate_stats')
        for name, dict_ in stats.iteritems():
            for key, value in dict_.iteritems():
                self.managed_files['stats_' + name].write(
                    str(key) +
                    ',' +
                    str(value) +
                    '\n')
        self.managed_files['stats_playback'].write(
            'startup_delay,' + str(self.startup_delay) + '\n')

    def _make_csv_from_list(self, list_, time_=True):
        """
        Convert a List object into CSV format and append the time to each row.
        """
        list_ = [str(i) for i in list_]
        if time_:
            return str(self.time_elapsed()) + ',' + ','.join(list_) + '\n'
        else:
            return str(','.join(list_) + '\n')

    def _csv_setup(self):
        """
        If a CSV file is new, insert a header row with the names of the fields.

        The column headers are derived from the dictionary keys.

        """
        for object_ in self._object_focus:
            header = self.player.retrieve_metric('report')[object_].keys()
            header.insert(0, 'elapsed_time')
            self.managed_files['report_' + object_].write(
                self._make_csv_from_list(
                    header,
                    time_=False))
            self.csv_new = False
            self._header_width = len(header)

    def csv_report(self):
        """Print a periodic report to file and/or STDOUT."""
        for object_ in self._object_focus:
            try:
                self.managed_files['report_' + object_].flush()
            except ValueError:
                pass
            try:
                report = self.player.retrieve_metric('report')[object_].values()
            except AttributeError:
                report = [0] * self._header_width
            try:
                report_csv = self._make_csv_from_list(report)
                self.managed_files['report_' + object_].write(report_csv)
            except ValueError:
                pass
            if self.player.options.debug:
                print ('[report][' + object_ + '] ' + report_csv),
            try:
                self.managed_files['report_' + object_].flush()
            except ValueError:
                pass

    def event(self, action, description):
        """Create a thread to handle event."""
        self.player.start_thread(self.event_thread, args=(action, description))

    def event_thread(self, action, description):
        """Event reporting to file."""
        time_elapsed = self.time_elapsed()
        if action == 'start' and description == 'playback':
            self.startup_delay = time_elapsed
        if self.player.options.csv:
            try:
                self.managed_files['event'].flush()
            except ValueError:
                pass
            output = (str(time_elapsed) + "," + str(action) + ","
                      + str(description) + "\n")
            try:
                self.managed_files['event'].write(output)
            except ValueError:
                pass
            if self.player.options.debug:
                print ("[event] " + output),
            try:
                self.managed_files['event'].flush()
            except ValueError:
                pass
