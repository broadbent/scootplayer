Scootplayer includes a number of configurable options. These can be found using the `-h` flag with Scootplayer. They are also listed below for your convenience.

### Flags ###

| Short Flag             | Long Flag                                 | Description                                                                              | Default     |
|------------------------|-------------------------------------------|------------------------------------------------------------------------------------------|-------------|
| -h                     | --help                                    | Show this table and exit                                                                 |             |
| -m MANIFEST            | --manifest=MANIFEST                       | Location of manifest to load                                                             |             |
| -o OUTPUT              | --output=OUTPUT                           | Location to store downloaded files and reports                                           | `out/`      |
|                        | --no-keep-alive                           | Prevent HTTP connection pooling and persistency                                          |             |
|                        | --max-playback-queue=MAX_PLAYBACK_QUEUE   | Set maximum size of playback queue in seconds                                            | 60 seconds  |
|                        | --max-download-queue=MAX_DOWNLOAD_QUEUE   | Set maximum size of download queue in seconds                                            | 30 seconds  |
| -d *or* -v             | --debug *or* --verbose                    | Print all output to console                                                              |             |
| -r REPORTING_PERIOD    | --reporting-period=REPORTING_PERIOD       | Set reporting period in seconds                                                          |             |
|                        | --no-csv                                  | Stop CSV writing                                                                         |             |
| -p PLAYLIST            | --playlist=PLAYLIST                       | Playlist of MPDs to play in succession                                                   |             |
| -x                     | --xml-validation                          | Validate the MPD against the MPEG-DASH schema                                            |             |
| -c REMOTE_CONTROL_HOST | --remote-control-host=REMOTE_CONTROL_HOST | Set hostname of the remote controller to listen to                                       | `localhost` |
|                        | --remote-control-port=REMOTE_CONTROL_PORT | Set port of the remote controller to listen to                                           | `5556`      |
| -t PLAYBACK_TIME       | --playback-time=PLAYBACK_TIME             | Playback content for given amount of seconds                                             |             |
| -w WINDOW_MULTIPLIER   | --window-multiplier=WINDOW_MULTIPLIER     | Moving average window calculated by multiplying,maximum segment duration with this value | 5           |
|                        | --vlc                                     | Emulate VLC playback behaviour                                                           |             |
|                        | --url                                     | Parse the URL to unreliably(!) determine playback,bitrate                                |             |
|                        | --connection-pool=CONN_POOL               | Set the amount of simultaneous connections that,can be made                              | 100         |
|                        | --process-pool=PROC_POOL                  | Set the amount of processes that can be used to,fetch the initialisation                 | 4           |
|                        | --no-write                                | Prevent the player writing downloaded files to disk                                      |             |
|                        | --max-retries                             | Set the amount of retries attempted when fetching remote content                         | 3           |
|                        | --threading                               | Use multithreading rather than multiprocessing when downloading the initialisations      |             |
|                        | --timeout                                 | Stop waiting for a response after a given number of seconds                              | 1           |
