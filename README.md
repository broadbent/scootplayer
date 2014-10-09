# Scootplayer #

An experimental MPEG-DASH request engine with support for accurate logging.

Downloads reuired files/byte ranges, but does not playback content. Can be used to simulate MPEG-DASH playback when viewing the video itself is not important. The motivation behind the creation of Scootplayer was to analyse the network characteristics of HTTP Adaptive Streaming (HAS) in a deterministic way.

Scootplayer provides rich logging information, which can be found in the output folder. This includes periodic reporting, events logging and overall statistics.

Scootplayer is intended for academic and experimental use only.

## Requirements ##

Install necessary packages with `pip`:
```bash
$ pip install -r requirements.txt
```

## Run ##

Scootplayer can be run using:
```bash
$ python scootplayer.py -m PATH_TO_MANIFEST_OR_URL
```
For more information on command-line flags, use:
```bash
$ python scootplayer.py -h
```

## Output ##

Scootplayer outputs files by default to the `out/` directory (by default). When Scootplayer is started, a new folder is created within `out/` with the current timestamp. This folder contains a number of Comma-Separated Value (CSV) files which store the logs themselves. Please see below for more details on these files. An additional `downloads/` folder is created within this. This contains the actual downloaded files which can be used for comparison, hashing, etc. This includes any MPD files if they are located remotely.

### report.csv ###

Contains a periodic log which updates every second. Each entry details the state of the download and playback queues. Also reports the current estimated bandwidth. Fields are described in the first row of the CSV file.

### event.csv ###

Contains an event driven log for precisely timing playback start and end times, in addition to other useful information.

### stats.csv ###

Produces a number of stats that are output when the player finishes playback. Fields are self-described in the file.

### Debug Output ###

Scootplayer implements a watchdog to detect stalled playback. If the player stops responding, Scootplayer will dump the status of current objects (playback and download queues, for example) to a file entitled named after the object. This is intended for debugging only: if there is no issue with playback, these files will not be present.

## Example MPDs ##

Example MPDs are found in the `examples/mpd` folder. These MPDs are not my own, nor do I host the content. These are taken from the [DASH dataset](http://www-itec.uni-klu.ac.at/ftp/datasets/mmsys12/BigBuckBunny/) over at [ITEC](http://www-itec.uni-klu.ac.at/).

## MPD Validation ##

Scootplayer supports the validation of MPD XML files using the [schema provided by the ISO](http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd). This schema (and its dependecies) can be found in the `validation` folder.

The schema included with Scootplayer is slightly modified from the original. The namespace, by default, is defined as `urn:mpeg:dash:schema:mpd:2011`. However, example MPDs, including those that ship with Scootplayer, often use a alternatively capitalised version of this namespace: `urn:mpeg:DASH:schema:MPD:2011`. Until this is normalised, we will follow the majority and support the alternative capitalisation.

It is important to consider that the validation process takes time. If you are using Scootplayer as a tool for evaluation, it may be prudent not to turn validation on. It is mainly intended as a debugging feature to help with the menagerie of old and non-standard MPDs available.

## Remote Control ## 

Multiple Scootplayer instances can be controlled through a single remote control. See `remote/scootplayer_remote_control.py` for more details.

## VLC Emulation ## 

Scootplayer can emulate VLC's MPEG-DASH playback behaviour. This is enabled using the `--vlc` flag. This is still an experimental feature, and likely to change as both VLC and Scootplayer are updated.

## License ##

This sofware is licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).

## Author ##

Scootplayer is developed and maintained by Matthew Broadbent (matt@matthewbroadbent.net). It can be found on GitHub at: http://github.com/broadbent/scootplayer.
