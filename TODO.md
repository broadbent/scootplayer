* Move to multiple representation objects
	* Contains URLs in a (dict or list) with all associated metadata
* SourceURL -> item method
* Overwrite bandwidth estimation class to emulate different players
* Load a 'playback' file to request specific chunks at specific times
* Load a 'traffic' file to emulate traffic conditions at given times
* zeromq interface to control clients and report stats