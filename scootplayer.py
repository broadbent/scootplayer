#!/usr/bin/env python2.7

"""Parses command line options and passes them to a new player."""

import scootplayer.player as player
import optparse

if __name__ == '__main__':
    PARSER = optparse.OptionParser()
    PARSER.set_defaults(output='out/', keep_alive=True,
                        max_playback_queue=60, max_download_queue=30, csv=True,
                        reporting_period=1, playlist=None, manifest=None,
                        xml_validation=False, remote_control_host='localhost',
                        remote_control_port='5556', playback_time=0,
                        window_multiplier=5, vlc=False, url=False,
                        conn_pool=100, proc_pool=4, write=True, max_retries=3,
                        threading=False, timeout=1, watchdog=True)
    PARSER.add_option("-m", "--manifest", dest="manifest",
                      help="location of manifest to load")
    PARSER.add_option("-o", "--output", dest="output",
                      help="""location to store downloaded files and reports
                      [default: %default]""")
    PARSER.add_option("--no-keep-alive", dest="keep_alive",
                      action="store_false",
                      help="prevent HTTP connection pooling and persistency")
    PARSER.add_option("--max-playback-queue", dest="max_playback_queue",
                      help="""set maximum size of playback queue in seconds
                      [default: %default seconds]""")
    PARSER.add_option("--max-download-queue", dest="max_download_queue",
                      help="""set maximum size of download queue in seconds
                      [default: %default seconds]""")
    PARSER.add_option("-d", "-v", "--debug", "--verbose", dest="debug",
                      action="store_true",
                      help="print all output to console")
    PARSER.add_option("-r", "--reporting-period", dest="reporting_period",
                      help="set reporting period in seconds")
    PARSER.add_option("--no-csv", dest="csv",
                      action="store_false", help="stop CSV writing")
    PARSER.add_option("-p", "--playlist", dest="playlist",
                      help="playlist of MPDs to play in succession")
    PARSER.add_option("-x", "--xml-validation", dest="xml_validation",
                      action="store_true",
                      help="validate the MPD against the MPEG-DASH schema")
    PARSER.add_option("-c", "--remote-control-host", dest="remote_control_host",
                      help="""set hostname of the remote controller to listen to
                      [default: %default]""")
    PARSER.add_option("--remote-control-port", dest="remote_control_port",
                      help="""set port of the remote controller to listen to
                      [default: %default]""")
    PARSER.add_option("-t", "--playback-time", dest="playback_time",
                      help="""playback content for given time (seconds)""")
    PARSER.add_option("-w", "--window-multiplier", dest="window_multiplier",
                      help="""moving average window calculated by multiplying
                      maximum segment duration with this value
                      [default: %default]""")
    PARSER.add_option("--vlc", dest="vlc", action="store_true",
                      help="""emulate VLC playback behaviour (experimental)
                      [default: %default]""")
    PARSER.add_option("--url", dest="url", action="store_true",
                      help="""parse the URL to unreliably(!) determine playback
                      bitrate [default: %default]""")
    PARSER.add_option("--connection-pool", dest="conn_pool",
                      help="""set the amount of simultaneous connections that
                      can be made [default: %default]""")
    PARSER.add_option("--process-pool", dest="proc_pool",
                      help="""set the amount of processes that can be used to
                      fetch the initialisation [default: %default]""")
    PARSER.add_option("--no-write", dest="write", action="store_false",
                      help="""prevent the player writing downloaded files to
                      disk [default: %default]""")
    PARSER.add_option("--max-retries", dest="max_retries",
                      help="""set the amount of retries attempted when fetching
                      remote content [default: %default]""")
    PARSER.add_option("--threading", dest="threading", action="store_true",
                      help="""use multithreading rather than multiprocessing
                      when downloading the initialisations""")
    PARSER.add_option("--timeout", dest="timeout",
                      help="""stop waiting for a response after a given number
                      of seconds [default: %default]""")
    PARSER.add_option("--no-watchdog", dest="watchdog", action="store_false",
                      help="""prevent the playback watchdog from running""")
    PARSER.add_option("-l", "--live-stats", dest="live", action="store_true",
                      help="""update playback statistics in realtime, rather
                      than at the end of playback (useful for visualisation)""")
    (OPTIONS, _) = PARSER.parse_args()
    if (OPTIONS.manifest is not None or OPTIONS.playlist is not None) and not \
        (OPTIONS.manifest and OPTIONS.playlist) \
            or OPTIONS.remote_control_host:
                player.Player(OPTIONS)
    else:
        PARSER.print_help()
