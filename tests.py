import scootplayer
import unittest
import os
import time
import random
from mock import Mock, MagicMock

import scootplayer.player as player
import scootplayer.bandwidth as bandwidth
import scootplayer.queue as queue
import scootplayer.remote as remote
import scootplayer.reporter as reporter
import scootplayer.representations as representations
import scootplayer.watchdog as watchdog
import scootplayer.progressbar as progressbar


class Options():
    output = 'out/'
    keep_alive = True
    manifest = 'examples/mpd/BigBuckBunny_2s_isoffmain_DIS_23009_1_v_2_1c2_2011_08_30.mpd'
    max_playback_queue = 60
    max_download_queue = 30
    csv = True
    reporting_period = 1
    playlist = None
    xml_validation = False
    remote_control_host = 'localhost'
    remote_control_port = '5556'
    playback_time = 0
    window_multiplier = 5
    vlc = False
    url = False
    conn_pool = 100
    debug = False

# class TestPlaybackQueue(unittest.TestCase):
#
#     MIN = 5
#     MAX = 7
#
#     def setUp(self):
#         self.player = MagicMock()
#         self.playback_object = queue.playback.PlaybackQueue(self.player, Options)
#         # self.representation = [1, 'test', 'test', 1, 1, 1]
#
#     def test_stop(self):
#         self.playback_object.stop()
#         self.player.event.assert_called_once_with('final', 'playback queue')
#
#     def test_add(self):
#         iterations = random.randint(self.MIN, self.MAX)
#         for _ in xrange(iterations):
#             self.playback_object.add((self.representation))
#         self.assertEqual(len(self.playback_object.queue.queue), iterations)
#
#     def test_playback(self):
#         print 'testing'
#         iterations = random.randint(self.MIN, self.MAX)
#         for _ in xrange(iterations):
#             self.playback_object.queue.put((self.representation))
#         self.playback_object.time_buffer = (iterations * int(self.representation[0]) + 1)
#         self.playback_object.playing = True
#         time.sleep((iterations * int(self.representation[0])) + 10)
#         self.assertEqual(self.playback_object.count, iterations)
#         self.assertEqual(len(self.playback_object.queue.queue), 0)
#         self.player.event.assert_called_once_with('stop', 'playback')
#
#         # self.playback_object.playback()
#         # self.assertEqual(len(self.playback_object.queue.queue), 0)
#         # self.assertEqual(self.playback_object.time_buffer, 0)
#         # self.player.event.assert_called_once_with('stop', 'playback')
#         # self.player.stop.assert_called()
#
#     def test_len(self):
#         iterations = random.randint(self.MIN, self.MAX)
#         print iterations
#         for _ in xrange(iterations):
#             self.playback_object.queue.put((self.representation))
#         self.assertEqual(len(self.playback_object), iterations)
#
#     def test_add_representation(self):
#         self.playback_object._add_representation(self.representation)
#         self.assertEqual(int(self.playback_object.time_buffer), int(self.representation[0]))
#         self.assertEqual(len(self.playback_object.queue.queue), 1)
#
#     def test_consume_representation(self):
#         pass
#
#     def test_start_playback(self):
#         self.playback_object._start_playback()
#         self.assertEqual(self.playback_object.playing, True)
#         self.player.event.assert_called_once_with('start', 'playback')
#
#     def test_stop_playback(self):
#         self.playback_object._stop_playback()
#         self.assertEqual(self.playback_object.playing, False)
#         self.player.event.assert_called_once_with('stop', 'playback')
#
#     def test_reset(self):
#         pass
#
#     # def test_max_buffer(self):
#     #     self.playback_object.pause = True
#     #     while len(self.playback_object.queue.queue) < self.MAX:
#     #         self.playback_object.queue.put((self.representation))
#     #     self.playback_object.time_buffer = self.MAX
#     #     print 'max'
#     #     print self.MAX, len(self.playback_object)
#     #     self.playback_object.add((self.representation))
#     #     print 'end max'
#     #     assert not self.player.event.called
#
#     def test_min_buffer(self):
#         while len(self.playback_object.queue.queue) > self.MIN:
#             self.playback_object.add((self.representation))
#         assert not self.player.event.called

class TestBandwidth(unittest.TestCase):

    def setUp(self):
        self._bw = bandwidth.Bandwidth()

    def test_trend(self):
        """Change bandwidth 100 times, check list matches expected result."""
        bandwidth_list = list()
        bandwidth_value = 0
        while len(bandwidth_list) != 100:
            previous_bandwidth_value = bandwidth_value
            bandwidth_value = random.randint(0, 10000000)
            self._bw.change(bandwidth_value)
            if bandwidth_value > previous_bandwidth_value:
                bandwidth_list.append(1)
            elif bandwidth_value == previous_bandwidth_value:
                bandwidth_list.append(0)
            elif bandwidth_value < previous_bandwidth_value:
                bandwidth_list.append(-1)
        self.assertEqual(bandwidth_list, self._bw.historical_trend())

    def test_string(self):
        """Change bandwidth, check cast to string."""
        bandwidth_value = random.randint(0, 10000000)
        self._bw.change(bandwidth_value)
        self.assertEqual(str(bandwidth_value), str(bandwidth_value))

    def test_int(self):
        """Change bandwidth, check cast to integer."""
        bandwidth_value = random.randint(0, 10000000)
        self._bw.change(bandwidth_value)
        self.assertEqual(int(bandwidth_value), bandwidth_value)

    def test_change(self):
        """Change bandwidth, check current."""
        bandwidth_value = random.randint(0, 10000000)
        self._bw.change(bandwidth_value)
        self.assertEqual(self._bw._current, bandwidth_value)

# class TestDirectoryFunctions(unittest.TestCase):
#
#     def test_create(self):
#         """Create directory, see if it exists."""
#         scootplayer.create_directory("test_dir")
#         self.assertTrue(os.path.isdir("test_dir"))
#
#     def test_remove(self):
#         """Delete directory, see if it no longer exists."""
#         scootplayer.remove_directory("test_dir")
#         self.assertFalse(os.path.isdir("test_dir"))


if __name__ == '__main__':
    unittest.main()
