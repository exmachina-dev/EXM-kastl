# -*- coding: utf-8 -*-

from threading import Thread
import time
import logging

logging = logging.getLogger('kastl.temperature')


class TempWatcher(object):

    callback = None

    def __init__(self, thermistor, fan, name):
        self.thermistor = thermistor
        self.fan = fan
        self.name = name
        self.current_temp = 0.0
        self.target_temp = 0.0
        self.max_temp = 0.0
        self.P = 0.1
        self.I = 0.005
        self.error_integral = 0.0
        self.running_time = 0.0
        self.interval = 1

    def set_target_temperature(self, temp):
        self.target_temp = float(temp)

    def set_max_temperature(self, temp):
        self.max_temp = float(temp)

    @property
    def temperature(self):
        return self.current_temp

    @property
    def target_reached(self):
        if self.target_temp == 0:
            return True
        err = abs(self.temperature - self.target_temp)
        return err < self.ok_range

    def enable(self, mode=True):
        self.enabled = True
        self.disabled = False
        if mode:
            self.t = Thread(target=self.keep_temperature)
        else:
            self.t = Thread(target=self.watch_temperature)
        self.t.daemon = True
        self.t.start()

    def disable(self):
        self.enabled = False

        while self.disabled is False:
            time.sleep(0.5)

        self.fan.set_power(0.0)

    def keep_temperature(self):
        while self.enabled:
            power = 1.0
            error = 0.0

            try:
                self.update_temp()

                error = self.target_temp - self.current_temp
                error *= -1

                self.running_time += self.interval
                _P = self.P * error

                self.error_integral += error * self.interval
                # Clamp error_integral to max output power; More reactive I
                self.error_integral = max(min(self.error_integral, 100.0), 00.0)
                _I = self.I * self.error_integral

                power = _P + _I
                power = max(min(power, 1.0), 0.0)
                logging.debug('Current temp for {}: {:.2f} deg C, Fan '
                              '{} set to {:.2f} | E: {:.2f} I: {}'.format(
                                  self.thermistor.name, self.current_temp,
                                  self.fan.channel, power, error,
                                  self.error_integral))
            except (ValueError, KeyError) as e:
                logging.warn('Unable to update temperature: {!s}'.format(e))

            self.fan.set_value(power)
            time.sleep(self.interval)
        self.disabled = True

    def watch_temperature(self):
        while self.enabled:
            try:
                self.update_temp()
            except (ValueError, KeyError) as e:
                logging.warn('Unable to update temperature: {!s}'.format(e))

            if self.current_temp >= self.max_temp:
                if self.callback:
                    self.callback()

            logging.debug('Current temp for {}: {:.2f} deg C'.format(
                self.thermistor.name, self.current_temp))
            time.sleep(self.interval)
        self.disabled = True

    def update_temp(self):
        self.current_temp = self.thermistor.temperature

        if self.current_temp >= self.max_temp:
            if self.callback:
                self.callback(self)
        return self.current_temp
