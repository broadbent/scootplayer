#!/usr/bin/env python2.7

import collections


class Bandwidth(object):
    """Object containing the current bandwidth estimation."""

    def __init__(self):
        self._current = 0
        self._previous = 0
        self._trend = collections.deque(maxlen=100)

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
