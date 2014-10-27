Scootplayer supports the loading of [MPEG-DASH](http://dashif.org/mpeg-dash/) Media Presentation Description (MPD) files.

A succinct description (with help from [Wikipedia](https://en.wikipedia.org/wiki/Dynamic_Adaptive_Streaming_over_HTTP)): An MPD *describes segment information (timing, URL, media characteristics such as video resolution and bit rates).*

## Examples ##

Example MPDs are found in the `examples/mpd` folder. These MPDs are not my own, nor do I host the content. These are taken from the [DASH dataset](http://www-itec.uni-klu.ac.at/ftp/datasets/mmsys12/BigBuckBunny/) over at [ITEC](http://www-itec.uni-klu.ac.at/).

## Validation ##

Scootplayer supports the validation of MPD XML files using the [schema provided by the ISO](http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd). This schema (and its dependecies) can be found in the `validation` folder.

The schema included with Scootplayer is slightly modified from the original. The namespace, by default, is defined as `urn:mpeg:dash:schema:mpd:2011`. However, example MPDs, including those that ship with Scootplayer, often use a alternatively capitalised version of this namespace: `urn:mpeg:DASH:schema:MPD:2011`. Until this is normalised, we will follow the majority and support the alternative capitalisation.

It is important to consider that the validation process takes time. If you are using Scootplayer as a tool for performance evaluation, it may be prudent not to turn validation on. It is mainly intended as a debugging feature to help with the menagerie of old and non-standard MPDs available.
