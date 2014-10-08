#!/usr/bin/env python2.7

"""Reporter used to report periodic statistics and events."""

import time


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
    managed_files = {'report': None,
                     'event': None,
                     'stats': None}

    def __init__(self, player):
        """Initialise files to save reports to."""
        self.player = player
        self.managed_files['report'] = self.player.open_file('/report.csv')
        self.managed_files['event'] = self.player.open_file('/event.csv')
        self.managed_files['stats'] = self.player.open_file('/stats.csv')
        self.start()

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
        self.start_time = time.time()
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
        if self.run:
            self.player.start_timed_thread(self.player.options.reporting_period,
                                           self.reporter)
            self.player.analysis()
            if self.player.options.csv:
                if self.csv_new:
                    self._csv_setup()
                self.csv_report()
        else:
            time.sleep(self.player.options.reporting_period)
            self.reporter()

    def _stats(self):
        """Retrieve statistics and print them to file."""
        stats = self.player.retrieve_metric('stats')
        for key, value in stats.items():
            self.managed_files['stats'].write(
                str(key) +
                ',' +
                str(value) +
                '\n')
        self.managed_files['stats'].write(
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
        header = self.player.retrieve_metric('report').keys()
        header.insert(0, 'elapsed_time')
        self.managed_files['report'].write(
            self._make_csv_from_list(
                header,
                time_=False))
        self.csv_new = False

    def csv_report(self):
        """Print a periodic report to file and/or STDOUT."""
        try:
            self.managed_files['report'].flush()
        except ValueError:
            pass
        try:
            report = self.player.retrieve_metric('report').values()
        except AttributeError:
            report = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        try:
            report_csv = self._make_csv_from_list(report)
            self.managed_files['report'].write(report_csv)
        except ValueError:
            pass
        if self.player.options.debug:
            print ("[report] " + report_csv),
        try:
            self.managed_files['report'].flush()
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
