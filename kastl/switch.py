#!/usr/bin/env python
"""
A class that listens for a button press
and sends an event if that happens.

This code is extracted from Redeem. Original source code can be found at:
    https://bitbucket.org/intelligentagent/redeem/src

Original author: Elias Bakken
Email: elias(dot)bakken(at)gmail(dot)com
Released under license: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

Code modified by Benoit Rapidel:
    Ported to python 3
    Better handling of direction and hit
    Removed PRU section
"""

from threading import Thread
import logging

logging = logging.getLogger('kastl.switch')


class Switch(object):

    callback = None                 # Override this to get events
    inputdev = "/dev/input/event1"  # File to listen to events

    def __init__(self, key_code, name):
        self.key_code = key_code
        self.name = name
        self.invert = False
        self.function = False
        self.hit = False
        self.direction = None

        self.t = Thread(target=self._wait_for_event)
        self.t.daemon = True
        self.t.start()

    @property
    def state(self):
        s = {
            'direction': self.direction,
            'function': self.function,
            'hit': self.hit,
            'key_code': self.key_code,
            'invert': self.invert,
            'name': self.name,
        }
        return s

    def _wait_for_event(self):
        evt_file = open(Switch.inputdev, "rb")
        while True:
            evt = evt_file.read(16)     # Read the event
            evt_file.read(16)           # Discard the debounce event
            code = evt[10]

            if code == self.key_code:
                self.direction = True if evt[12] else False
                self.hit = False

                if self.invert is True and self.direction is True:
                    self.hit = True
                elif self.invert is False and self.direction is False:
                    self.hit = True

                if Switch.callback is not None:
                    try:
                        Switch.callback(self.state)
                    except Exception as e:
                        logging.warn('Exception in {!s}: {!s}'.format(self, e))
            else:
                self.direction = None

    def __repr__(self):
        i = {
            'name': self.name,
            'keycode': self.key_code,
            'dir': self.direction,
            'hit': self.hit,
        }

        return 'Switch {name} at {keycode} (dir {dir} hit {hit})'.format(**i)

if __name__ == '__main__':
    import signal

    def cb(event):
        print(event)

    Switch.callback = cb
    keycodes = (112, 113, 114, 115, 116)
    for k in keycodes:
        n = 'SW%i' % (k - 112)
        s = Switch(k, n)

    signal.pause()
