#!/usr/bin/env python2.7

import scootplayer.player as player
import optparse

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.set_defaults(output='out/', keep_alive=True,
                        max_playback_queue=60, max_download_queue=30, csv=True,
                        gauged=False, reporting_period=1, playlist=None,
                        manifest=None, xml_validation=False,
                        remote_control_host='localhost',
                        remote_control_port='5556', playback_time=0,
			window_multiplier=5, vlc=False, url=False)
    parser.add_option("-m", "--manifest", dest="manifest",
                      help="location of manifest to load")
    parser.add_option("-o", "--output", dest="output",
                      help="""location to store downloaded files and reports
                      [default: %default]""")
    parser.add_option("--no-keep-alive", dest="keep_alive",
                      action="store_false",
                      help="prevent HTTP connection pooling and persistency")
    parser.add_option("--max-playback-queue", dest="max_playback_queue",
                      help="""set maximum size of playback queue in seconds
                      [default: %default seconds]""")
    parser.add_option("--max-download-queue", dest="max_download_queue",
                      help="""set maximum size of download queue in seconds
                      [default: %default seconds]""")
    parser.add_option("-d", "-v", "--debug", "--verbose", dest="debug",
                      action="store_true",
                      help="print all output to console")
    parser.add_option("-r", "--reporting-period", dest="reporting_period",
                      help="set reporting period in seconds")
    parser.add_option("--no-csv", dest="csv",
                      action="store_false",
                      help="stop CSV writing")
    parser.add_option("-p", "--playlist", dest="playlist",
                      help="playlist of MPDs to play in succession")
    parser.add_option("-x", "--xml-validation", dest="xml_validation",
                      action="store_true",
                      help="validate the MPD against the MPEG-DASH schema")
    parser.add_option("-c", "--remote-control-host", dest="remote_control_host",
                      help="""set hostname of the remote controller to listen to
                      [default: %default]""")
    parser.add_option("--remote-control-port", dest="remote_control_port",
                      help="""set port of the remote controller to listen to
                      [default: %default]""")
    parser.add_option("-t", "--playback-time", dest="playback_time",
                      help="""playback content for given time (seconds)""")
    parser.add_option("-w", "--window-multiplier", dest="window_multiplier",
                      help="""moving average window calculated by multiplying 
		      maximum segment duration with this value 
		      [default: %default])""")
    parser.add_option("--vlc", dest="vlc", action="store_true", 
		      help="""emulate VLC playback behaviour [default: %default]""")
    parser.add_option("--url", dest="url", action="store_true", 
		      help="""parse the URL to unreliably determine playback 
		      bitrate [default: %default]""")
    (options, args) = parser.parse_args()
    if (options.manifest is not None or options.playlist is not None) and not \
            (options.manifest and options.playlist) \
            or options.remote_control_host:
            player.Player(options)
    else:
        parser.print_help()
