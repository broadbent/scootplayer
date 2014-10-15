#!/usr/bin/env python2.7

"""Remote control functionality on the player side."""

import zmq
import time


class RemoteControl(object):

    """
    Receives commands from remote control application and executes
    corresponding actions.

    """

    run = False
    socket = None

    def __init__(self, player, options):
        """Start thread to listen to commands from remote control."""
        self.player = player
        self.options = options
        self.player.start_thread(self._listen)

    def pause(self):
        """Pause listening to commands from remote control."""
        self.run = False

    def resume(self):
        """Resume listening to commands from remote control."""
        self.run = True

    def stop(self):
        """Stop listening to commands from remote control."""
        self.socket.close()
        self.player.event('stop', 'remote')

    def _listen(self):
        """Listen to commands from remote control."""
        context = zmq.Context()
        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://%s:%s" % (self.options.remote_control_host,
                                             self.options.remote_control_port))
        self.socket.setsockopt(zmq.SUBSCRIBE, '')
        while True:
            if self.run:
                string = self.socket.recv()
                resource = ''
                try:
                    action, resource = string.split()
                except ValueError:
                    action = string
                action, resource = action.strip(), resource.strip()
                self._lookup_method(action)(resource)
            else:
                time.sleep(0.1)

    def _lookup_method(self, action):
        """Call the appropriate method given the action."""
        return getattr(self, 'do_' + action, None)

    def do_play(self, resource):
        """
        Handle a `play` command from the remote controller.

        If a resource is given, stop playback, clear playlist and add the item
        to the playlist queue. Then, play this item.

        If a resource is not given, resume current playback if paused.
        """
        if resource == '' and self.player.state == 'stop':
            return
        elif resource != '':
            try:
                self.player.event('remote', 'play: ' + str(resource))
            except AttributeError:
                pass  # Reporter not yet initialised
            self.player.pause()
            self.player.playlist.stop()
            self.player.playlist.add(resource)
            self.player.next()
            self.player.resume()
        else:
            try:
                self.player.event('remote', 'play')
            except AttributeError:
                pass  # Reporter not yet initialised - need to restart reporter
            try:
                self.player.resume()
            except AttributeError:
                pass  # Player is not playing!

    def do_add(self, resource):
        """Handle an `add` command from the remote controller.

        Add an item to the playlist queue.
        """
        self.player.event('remote', 'add: ' + str(resource))
        self.player.playlist.add(resource)

    def do_pause(self, _):
        """Handle a `pause` command from the remote controller.

        Pause playback on the player.
        """
        self.player.event('remote', 'pause')
        self.player.pause()

    def do_stop(self, _):
        """Handle a `stop` command from the remote controller.

        Pause playback on the player, and then stop playback.
        """
        self.player.event('remote', 'stop')
        self.player.pause()
        self.player.stop()

    def do_exit(self, _):
        """Handle an `exit` command from the remote controller.

        Exit the player.
        """
        self.player.event('remote', 'exit')
        self.player.exit()
