import scootplayer
import unittest
import os
import time
import random
from mock import Mock, MagicMock

class Options():
    manifest = 'examples/mpd/combined_test.mpd'
    playlist = 'examples/playlist/sample.m3u'
    output = 'output'
    keep_alive = True
    gauged = False

class TestPlaybackQueue(unittest.TestCase):

    MIN = 5
    MAX = 7

    def setUp(self):
        self.player = MagicMock()
        self.playback_object = scootplayer.PlaybackQueue(self.player, self.MIN, self.MAX)
        self.representation = [1, 'test', 'test', 1, 1, 1]

    def test_stop(self):
        self.playback_object.stop()
        self.player.reporter.event.assert_called_once_with('final', 'playback queue')

    def test_add(self):
        iterations = random.randint(self.MIN, self.MAX)
        for _ in xrange(iterations):
            self.playback_object.add((self.representation))
        self.assertEqual(len(self.playback_object.queue.queue), iterations)

    def test_playback(self):
        print 'testing'
        iterations = random.randint(self.MIN, self.MAX)
        for _ in xrange(iterations):
            self.playback_object.queue.put((self.representation))
        self.playback_object.time_buffer = (iterations * int(self.representation[0]) + 1)
        self.playback_object.playing = True
        time.sleep((iterations * int(self.representation[0])) + 10)
        self.assertEqual(self.playback_object.count, iterations)
        self.assertEqual(len(self.playback_object.queue.queue), 0)
        self.player.reporter.event.assert_called_once_with('stop', 'playback')

        # self.playback_object.playback()
        # self.assertEqual(len(self.playback_object.queue.queue), 0)
        # self.assertEqual(self.playback_object.time_buffer, 0)
        # self.player.reporter.event.assert_called_once_with('stop', 'playback')
        # self.player.stop.assert_called()

    def test_len(self):
        iterations = random.randint(self.MIN, self.MAX)
        print iterations
        for _ in xrange(iterations):
            self.playback_object.queue.put((self.representation))
        self.assertEqual(len(self.playback_object), iterations)

    def test_add_representation(self):
        self.playback_object._add_representation(self.representation)
        self.assertEqual(int(self.playback_object.time_buffer), int(self.representation[0]))
        self.assertEqual(len(self.playback_object.queue.queue), 1)

    def test_consume_representation(self):
        pass

    def test_start_playback(self):
        self.playback_object._start_playback()
        self.assertEqual(self.playback_object.playing, True)
        self.player.reporter.event.assert_called_once_with('start', 'playback')

    def test_stop_playback(self):
        self.playback_object._stop_playback()
        self.assertEqual(self.playback_object.playing, False)
        self.player.reporter.event.assert_called_once_with('stop', 'playback')

    def test_reset(self):
        pass

    # def test_max_buffer(self):
    #     self.playback_object.pause = True
    #     while len(self.playback_object.queue.queue) < self.MAX:
    #         self.playback_object.queue.put((self.representation))
    #     self.playback_object.time_buffer = self.MAX
    #     print 'max'
    #     print self.MAX, len(self.playback_object)
    #     self.playback_object.add((self.representation))
    #     print 'end max'
    #     assert not self.player.reporter.event.called

    def test_min_buffer(self):
        while len(self.playback_object.queue.queue) > self.MIN:
            self.playback_object.add((self.representation))
        assert not self.player.reporter.event.called

class TestBandwidthFunctions(unittest.TestCase):

    def test_trend(self):
        """Change bandwidth 100 times, check list matches expected result."""
        bandwidth_object = scootplayer.Bandwidth()
        bandwidth_list = list()
        bandwidth_value = 0
        while len(bandwidth_list) != 100:
            previous_bandwidth_value = bandwidth_value
            bandwidth_value = random.randint(0, 10000000)
            bandwidth_object.change(bandwidth_value)
            if bandwidth_value > previous_bandwidth_value:
                bandwidth_list.append(1)
            elif bandwidth_value == previous_bandwidth_value:
                bandwidth_list.append(0)
            elif bandwidth_value < previous_bandwidth_value:
                bandwidth_list.append(-1)
        self.assertEqual(bandwidth_list, bandwidth_object.historical_trend())

    def test_string(self):
        """Change bandwidth, check cast to string."""
        bandwidth_object = scootplayer.Bandwidth()
        bandwidth_value = random.randint(0, 10000000)
        bandwidth_object.change(bandwidth_value)
        self.assertEqual(str(bandwidth_value), str(bandwidth_value))

    def test_int(self):
        """Change bandwidth, check cast to integer."""
        bandwidth_object = scootplayer.Bandwidth()
        bandwidth_value = random.randint(0, 10000000)
        bandwidth_object.change(bandwidth_value)
        self.assertEqual(int(bandwidth_value), bandwidth_value)

    def test_change(self):
        """Change bandwidth, check current."""
        bandwidth_object = scootplayer.Bandwidth()
        bandwidth_value = random.randint(0, 10000000)
        bandwidth_object.change(bandwidth_value)
        self.assertEqual(bandwidth_object._current, bandwidth_value)

class TestDirectoryFunctions(unittest.TestCase):

    def test_create(self):
        """Create directory, see if it exists."""
        scootplayer.create_directory("test_dir")
        self.assertTrue(os.path.isdir("test_dir"))

    def test_remove(self):
        """Delete directory, see if it no longer exists."""
        scootplayer.remove_directory("test_dir")
        self.assertFalse(os.path.isdir("test_dir"))


if __name__ == '__main__':
    unittest.main()
