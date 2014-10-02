#!/usr/bin/env python2.7

import time

class Reporter(object):
    """Object used to report both periodic statistics and events."""

    player = None
    start_time = 0
    report_file = None
    event_file = None
    stats_file = None
    report = False
    options = None
    run = False
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
        self.stats()
        for _, obj in self.managed_files.items():
            try:
                getattr(obj, 'close')()
            except Exception:
                pass
        self.player.event('stop', 'reporter')

    def pause(self):
        self.run = False

    def resume(self):
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
        """Periodic reporting of various stats (every second) to file."""
        time_elapsed = self.time_elapsed()
        if self.run:
            self.player.start_timed_thread(self.player.options.reporting_period,
                self.reporter)
            self.player.analysis()
            if self.player.options.csv:
		if self.csv_new:
		    self.csv_setup()
                self.csv_report(time_elapsed)
        else:
            time.sleep(self.player.options.reporting_period)
            self.reporter()

    def stats(self):
        stats = self.player.retrieve_metric('stats')
        for key, value in stats.items():
            self.managed_files['stats'].write(str(key) + ',' + str(value) + '\n')
        self.managed_files['stats'].write('startup_delay,' + str(self.startup_delay) + '\n')

    def _make_csv_from_list(self, _list, time=True):
	_list = [str(i) for i in _list]
	if time:
            return str(self.time_elapsed()) + ',' + ','.join(_list) + '\n'
	else:
            return str(','.join(_list) + '\n')
	    
    def csv_setup(self):
	header = self.player.retrieve_metric('report').keys()
	header.insert(0, 'elapsed_time')
	self.managed_files['report'].write(self._make_csv_from_list(header, time=False))
	self.csv_new = False

    def csv_report(self, time_elapsed):
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
