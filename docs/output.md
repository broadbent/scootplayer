Scootplayer outputs files to the `out/` directory (by default). When Scootplayer is started, a new folder is created within `out/` with the current timestamp. This folder (and its subfolders) contain a number of Comma-Separated Value (CSV) files which store the logging information from Scootplayer. Please see below for more details on these files.

### Reporting ###

Periodic logs are updated every second (by default). The are stored in the `report/` directory in multiple files. Each file represents the two main queues used in Scootplayer: `playback.csv` and `download.csv`. Each entry details the state of these queues. The column names are detailed in the first row of the CSV file.

### Statistics ###

A number of stats that are generated when the player finishes playback. The are stored in the `stats/` directory in multiple files. Each file represents the two main queues used in Scootplayer: `playback.csv` and `download.csv`. The column names are detailed in the first row of the CSV file.

### Events ###

An event driven log for precisely reporting certain important occurences. This is stored in the `event.csv` file. Each event should be self-described.

### Downloads ###

Any downloaded files are stored in the `downloads/` folder. These can be used for comparison, hashing, integrity checking etc. This includes any MPD files if they are located remotely (stored in an `mpd/` subfolder).

### Runtime Information ###

Various relevant pieces of information are made available in the `info.csv` file. This helps to normalise experimental runs and provides basic debugging information. It is available after ~5 seconds of playback.

### Debugging ###

Scootplayer implements a watchdog to detect stalled playback. If the player stops responding, Scootplayer will dump the status of current objects (playback and download queues, for example) to a file entitled named after the object. These files are contained within the `dump/` folder. This is information is intended for debugging only: if there is no issue with playback, this folder and the files within will not be present.
