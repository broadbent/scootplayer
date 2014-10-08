#!/usr/bin/env python2.7

"""A visualisation of playback progress using a bar."""

from progress.bar import Bar


class NullBar(Bar):
    """Use an empty bar if in debug mode."""

    def __init__(self):
        """Do nothing on initialisation."""
        pass

    def next(self, n=1):
        """Do nothing on update."""
        pass


class PlaybackBar(Bar):
    """Playback Bar used during playback to represent progress."""

    def __init__(self, *args, **kwargs):
        """Initialise the bar with default settings.

        Include relevant playback information, such as the elapsed amount of
        time, the total amount of time and the current state of the player.
        """
        self.player = kwargs['player']
        super(PlaybackBar, self).__init__(*args, **kwargs)
        total = "%02d:%02d" % (divmod(self.max, 60))
        self.suffix = '%(elapsed)s / ' + total + ' / ' + '%(state)s'

    @property
    def elapsed(self):
        """Get the currently elapsed amount of seconds."""
        return "%02d:%02d" % (divmod(self.index, 60))

    @property
    def state(self):
        """Get the current state of the player."""
        return self.player.state
