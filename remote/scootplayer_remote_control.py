#!/usr/bin/env python2.7

"""Remote control for multiple remote Scootplayer clients."""

import zmq
import sys
import cmd


class ScootplayerRemoteControl(cmd.Cmd):

    """Remote control for multiple remote Scootplayer clients."""

    intro = """Welcome to the Scootplayer Remote Control.
	       Type help or ? to list commands.\n"""
    prompt = '(scootplayer) '

    def do_play(self, arg):
        """
        Start playback on listening Scootplayers. Optionally include a
        path on the local filesystem or a URL to download.

        """
        send_message('play', arg)

    def do_add(self, arg):
        """
        Add an MPD to listening Scootplayers playlists. Include a path on
        the local filesystem or a URL to download.

        """
        send_message('add', arg)

    def do_pause(self, _):
        """
        Pause playback on listening Scootplayers. Will NOT terminate clients.
        Resume playback using the `play` command.

        """

        send_message('pause')

    def do_stop(self, _):
        """
        Stop playback on listening Scootplayers. Will NOT terminate clients,
        but will clear their playlist.

        """
        send_message('stop')

    def do_exit(self, _):
        "Terminate the execution of listening Scootplayers."
        send_message('exit')

    def do_quit(self, _):
        "Quit the Scootplayer Remote Control."
        print 'Thank you for using the Scootplayer Remote Control.'
        return True


def send_message(action, url=''):
    """Send a string to listening players."""
    SOCKET.send("%s %s" % (action, url))

if __name__ == '__main__':
    try:
        PORT = sys.argv[1]
    except IndexError:
        PORT = "5556"
    CONTEXT = zmq.Context()
    SOCKET = CONTEXT.socket(zmq.PUB)
    SOCKET.bind("tcp://*:%s" % PORT)
    ScootplayerRemoteControl().cmdloop()
