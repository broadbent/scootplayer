# scootplayer #

An experimental MPEG-DASH request engine with support for accurate logging.

Downloads reuired files/ranges, but does not playback content. Can be used to simulate MPEG-DASH playback when viewing the video itself is not important.

Provides rich logging information, which can be found in the output folder.

Intended for academic and experimental use only.

## Requirements ##

`scootplayer` uses the excellent [`requests`](https://github.com/kennethreitz/requests) package to support HTTP connection pooling and persistency.

Install necessary packages with `pip`:
```bash
$ pip install -r requirements.txt
```

## Run ##

`scootplayer` can be run using:
```bash
$ python scootplayer.py -m PATH_TO_MANIFEST_OR_URL
```
For more information on command-line flags, use:
```bash
$ python scootplayer.py -h
```

## Output ##

`scootplayer` outputs files by default to the `out/` directory. When `scootplayer` is started, a new folder is created within `out/` with the current timestamp. This folder then contains two Comma-Separated Value (CSV) files which store the logs themselves. An additional `downloads/` folder is created within this. This contains the actual downloaded files which can be used for comparison, hashing, etc.

### report.csv ###

Contains a periodic log which updates every second. Each entry details the state of the download and playback queues. Also reports the current estimated bandwidth.

### event.csv ###

Contains an event driven log for precisely timing playback start and end times, in addition to other useful information.

## Example MPDs ##

Example MPDs are found in the `examples/mpd` folder. These MPDs are not my own, nor do I host the content. These are taken from the [DASH dataset](http://www-itec.uni-klu.ac.at/ftp/datasets/mmsys12/BigBuckBunny/) over at [ITEC](http://www-itec.uni-klu.ac.at/).

## Experimental Features ##

A draft Gnuplot script is included in `examples/gnuplot` folder. This creates a postscript file visualising the bits per second observed by the download and playback queues.

Support for [gauged](https://github.com/chriso/gauged/tree/master) available. Requires a local MySQL database named `gauged`. Use the `-g` flag to enable.

## License ##

This sofware is licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).

## Author ##

`scootplayer` is developed and maintained by Matthew Broadbent (matt@matthewbroadbent.net). It can be found on GitHub at: http://github.com/broadbent/scootplayer.
