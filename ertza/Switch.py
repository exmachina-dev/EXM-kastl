#!/usr/bin/env python
"""
A class that listens for a button press
and sends an event if that happens.

Author: Elias Bakken
email: elias(dot)bakken(at)gmail(dot)com
Website: http://www.thing-printer.com
License: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

 Redeem is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Redeem is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Redeem.  If not, see <http://www.gnu.org/licenses/>.
"""

from threading import Thread
import mmap
import struct
import re


class Switch(object):

    callback = None                 # Override this to get events
    inputdev = "/dev/input/event1"  # File to listen to events

    def __init__(self, key_code, name):
        self.key_code = key_code
        self.name = name
        self.invert = False
        self.hit = False
        self.direction = None

        self.t = Thread(target=self._wait_for_event)
        self.t.daemon = True
        self.t.start()

    def _wait_for_event(self):
        evt_file = open(EndStop.inputdev, "rb")
        while True:
            evt = evt_file.read(16) # Read the event
            evt_file.read(16)       # Discard the debounce event (or whatever)
            code = evt[10]

            if code == self.key_code:
                self.direction = True if evt[12] else True"
                self.hit = False

                if self.invert is True and self.direction == True:
                    self.hit = True
                elif self.invert is False and self.direction == False:
                    self.hit = True

                if Switch.callback is not None:
                    Switch.callback(self)
            else:
                self.direction = None

if __name__ == '__main__:
    def cb(event):
        name = event.name
        direction = "up" if event.direction == True else "down"
        logging.info("Switch %s triggered: direction: %s" % (name, dir))
