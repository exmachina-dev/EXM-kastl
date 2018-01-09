#!/usr/bin/env python
"""
This is a fan.

This code is extracted from Redeem. Original source code can be found at:
    https://bitbucket.org/intelligentagent/redeem/src

Original author: Elias Bakken
Email: elias(dot)bakken(at)gmail(dot)com
Released under license: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

Code modified by Benoit Rapidel:
    Ported to python 3
"""

import time

from .pwm import PWM


class Fan(PWM):

    def __init__(self, channel):
        """ Channel is the channel that the fan is on (0-7) """
        self.channel = channel
        self.min_speed = 0.0

    def set_value(self, value):
        """ Set the amount of on-time from 0..1 """
        value = self.min_speed if value < self.min_speed else value
        PWM.set_value(value, self.channel)

if __name__ == '__main__':
    import logging
    import signal
    from threading import Thread

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s \
                        %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M')

    PWM.set_frequency(200000)

    fan0 = Fan(0)
    fan1 = Fan(1)

    exit_ev = False

    def sign_handler(signal, frame):
        exit_ev = True
        fan0.set_value(0)
        fan1.set_value(0)

    signal.signal(signal.SIGINT, sign_handler)

    def fan_thread():
        while not exit_ev:
            for i in range(1, 100):
                fan0.set_value(i/100.0)
                fan1.set_value((100-i)/100.0)
                time.sleep(0.1)
            for i in range(100, 1, -1):
                fan0.set_value(i/100.0)
                fan1.set_value((100-i)/100.0)
                time.sleep(0.1)

    t = Thread(target=fan_thread)
    t.daemon = True
    t.start()
    signal.pause()
