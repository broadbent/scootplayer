Scootplayer is an experimental MPEG-DASH request engine with support for accurate logging.

Downloads the required files/byte ranges, but does not playback content. Can be used to simulate MPEG-DASH playback when viewing the video itself is not important. The motivation behind the creation of Scootplayer was to analyse the network characteristics of HTTP Adaptive Streaming (HAS) traffic in a deterministic way.

Scootplayer provides rich logging information. This includes periodic reporting, event logging and playback statistics.

## Get Scootplayer ##

Retrieve Scootplayer with `git`:
```bash
$ git clone https://github.com/broadbent/scootplayer.git
```

## Requirements ##

Install necessary packages with `pip`:
```bash
$ pip install -r requirements.txt
```

## Quick Start ##

To get started, Scootplayer can be run using:
```bash
$ python scootplayer.py -m PATH_TO_MANIFEST_OR_URL
```

For more information on command-line flags, use:
```bash
$ python scootplayer.py -h
```

## Documentation ##

Further documentation is available at [http://scootplayer.readthedocs.org](https://scootplayer.readthedocs.org).
