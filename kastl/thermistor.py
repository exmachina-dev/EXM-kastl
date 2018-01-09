# -*- coding: utf-8 -*-

from threading import Lock
import logging

logging = logging.getLogger('kastl.thermistor')

from .temp_chart import temp_chart

_ADC_PATH = "/sys/bus/iio/devices/iio:device0"


def transpose(it):
    temp = list()
    adcv = list()

    for l in it:
        if len(l) != 2:
            raise ValueError('Tuple misformatted')

        temp.append(l[0])
        adcv.append(l[1])

    return tuple((temp, adcv))


class Thermistor(object):

    temp_table = transpose(temp_chart['NTCLE100E3103JB0'])
    mutex = Lock()

    def __init__(self, pin, name):
        self.broken_resistor = 200000

        self.pin = "%s/in_voltage%d_raw" % (_ADC_PATH, pin)
        self.name = name

    @property
    def temperature(self):
        temp = -1.0
        Thermistor.mutex.acquire()

        try:
            with open(self.pin, "r") as f:
                voltage = (float(f.read().rstrip()) / 4095.0) * 1.8
                res_val = self.voltage_to_resistance(voltage)
                temp = self.resistance_to_degrees(res_val)
        except IOError as e:
            logging.warn("Unable to get temperature from %s" % self.name)
            logging.exception(e)
        finally:
            Thermistor.mutex.release()

        return temp

    def resistance_to_degrees(self, resistor_val):
        if resistor_val > self.broken_resistor:
            raise ValueError('Resistance value is off limit. Possible broken connection')

        idx = -1
        for i, v in enumerate(Thermistor.temp_table[1]):
            if v - resistor_val <= 0:
                idx = i
                break

        if idx == -1:
            raise KeyError('Unable to find temperature for {}'.format(resistor_val))

        Ta = (Thermistor.temp_table[0][idx] - Thermistor.temp_table[0][idx-1])
        Tb = (Thermistor.temp_table[1][idx-1] - Thermistor.temp_table[1][idx])
        Ta /= Tb
        Tb = Thermistor.temp_table[0][idx-1] - Ta * Thermistor.temp_table[1][idx]

        return Ta * resistor_val + Tb

    def voltage_to_resistance(self, v_sense):
        if v_sense == 0 or (abs(v_sense - 1.8) < 0.001):
            return 10000000.0
        return 4700.0 / ((1.8 / v_sense) - 1.0)
