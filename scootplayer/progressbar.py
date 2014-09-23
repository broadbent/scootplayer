#!/usr/bin/env python2.7

from progress.bar import Bar


class NullBar():

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
