#!/usr/bin/env python2.7

import zmq
import time


class RemoteControl():

    run = False

    def __init__(self, player, options):
        self.player = player
        self.options = options
        self.player.start_thread(self._listen)

    def stop(self):
        self.socket.close()
        self.player.event('stop', 'remote')

    def _listen(self):
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
                except:
                    action = string
                action, resource = action.strip(), resource.strip()
                self._lookup_method(action)(resource)
            else:
                time.sleep(1)

    def _lookup_method(self, action):
        return getattr(self, 'do_' + action, None)

    def do_play(self, resource):
        if resource == '' and self.player.state == 'stop':
            return
        elif resource != '':
            try:
                self.player.event('remote', 'play: ' + str(resource))
            except:
                pass  # Reporter not yet initialised
            self.player.pause()
            self.player.playlist.stop()
            self.player.playlist.add(resource)
            self.player.next()
            self.player.resume()
        else:
            try:
                self.player.event('remote', 'play')
            except:
                pass  # Reporter not yet initialised - need to restart reporter
            try:
                self.player.resume()
            except:
                pass  # Player is not playing!

    def do_add(self, resource):
        self.player.event('remote', 'add: ' + str(resource))
        self.player.playlist.add(resource)

    def do_pause(self, _):
        self.player.event('remote', 'pause')
        self.player.pause()

    def do_stop(self, _):
        self.player.event('remote', 'stop')
        self.player.pause()
        self.player.stop()

    def do_exit(self, _):
        self.player.event('remote', 'exit')
        self.player.exit()
