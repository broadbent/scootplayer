import gst
from gst.pbutils import Discoverer

d = Discoverer(5000000000)
vid_info = d.discover_uri("file://home/broadbent/Workspace/scootplayer/out/") # needs to be a full path
duration = vid_info.get_duration()
