#!/usr/bin/env python
"""
This is an implementation of the PWM DAC

This code is extracted from Redeem. Original source code can be found at:
    https://bitbucket.org/intelligentagent/redeem/src

Original author: Elias Bakken
Email: elias(dot)bakken(at)gmail(dot)com
Released under license: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

Code modified by Benoit Rapidel:
    Ported to python 3
"""

import time
import subprocess

from .adafruit_i2c import Adafruit_I2C


class PWM(object):

    frequency = 0
    i2c = None

    PCA9685_MODE1 = 0x0
    PCA9685_PRESCALE = 0xFE

    @staticmethod
    def __init_pwm():
        PWM.i2c = Adafruit_I2C(0x70, 2, False)  # Open device
        PWM.i2c.write8(PWM.PCA9685_MODE1, 0x01)    # Reset


    @staticmethod
    def set_frequency(freq):
        """ Set the PWM frequency for all fans connected on this PWM-chip """

        if PWM.i2c is None:
            PWM.__init_pwm()
        prescaleval = 25000000
        prescaleval /= 4096
        prescaleval /= float(freq)
        prescaleval = int(prescaleval + 0.5)
        prescaleval -= 1

        oldmode = PWM.i2c.readU8(PWM.PCA9685_MODE1)
        newmode = (oldmode & 0x7F) | 0x10
        PWM.i2c.write8(PWM.PCA9685_MODE1, newmode)
        PWM.i2c.write8(PWM.PCA9685_PRESCALE, prescaleval)
        PWM.i2c.write8(PWM.PCA9685_MODE1, oldmode)
        time.sleep(0.05)
        PWM.i2c.write8(PWM.PCA9685_MODE1, oldmode | 0xA1)

        PWM.frequency = freq

    @staticmethod
    def set_value(value, channel):
        """ Set the amount of on-time from 0..1 """
        off = int(value*4095)
        byte_list = [0x00, 0x00, off & 0xFF, off >> 8]
        PWM.i2c.writeList(0x06+(4*channel), byte_list)

if __name__ == '__main__':
    import os
    import logging

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M')


    PWM.set_frequency(100)

    for i in xrange(1,4095):
        logging.info(i)
        PWM.set_value(i/4095.0, 0)
        PWM.set_value(i/4095.0, 1)

