#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Main class for ertza

import logging
import os
import os.path
import sys
import signal
from threading import Thread
from multiprocessing import JoinableQueue

from ConfigParser import ConfigParser
from Machine import Machine
from PWM import PWM
try:
    from Thermistor import Thermistor
    NO_TH = False
except ImportError:
    NO_TH = True

from Fan import Fan
from Switch import Switch
from TempWatcher import TempWatcher
from Led import Led

version = "0.0.2~Firstimer"

_DEFAULT_CONF = "/etc/ertza/default.conf"
_MACHINE_CONF = "/etc/ertza/machine.conf"
_CUSTOM_CONF = "/etc/ertza/custom.conf"

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s \
                    %(levelname)-8s %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S')


class Ertza(object):
    """
    Main class for ertza.

    Handle log, configuration, startup and dispatch others tasks to
    various processes
    """

    def __init__(self, *agrs, **kwargs):
        """ Init """
        logging.info("Ertza initializing. Version: " + version)

        machine = Machine()
        self.machine = machine

        if not os.path.isfile(_DEFAULT_CONF):
            logging.error(_DEFAULT_CONF + " does not exist, exiting.")
            sys.exit()

        machine.config = ConfigParser(_DEFAULT_CONF,
                                      _MACHINE_CONF,
                                      _CUSTOM_CONF)

        # Get loglevel from config file
        level = self.machine.config.getint('system', 'loglevel')
        if level > 0:
            logging.info("Setting loglevel to %d" % level)
            logging.getLogger().setLevel(level)

        drv = machine.init_driver()
        if drv:
            logging.info("Loaded %s driver for machine" % drv)
        else:
            logging.error("Unable to find driver, exiting.")
            sys.exit()

        PWM.set_frequency(1000)

        if not NO_TH:
            self._config_thermistors()
        self._config_fans()
        self._config_external_switches()
        self._config_leds()

        # Create queue of commands
        self.machine.commands = JoinableQueue(10)
        self.machine.unbuffered_commands = JoinableQueue(10)
        self.machine.sync_commands = JoinableQueue()

    def start(self):
        """ Start the processes """
        self.running = True

        # Start the processes
        thread0 = Thread(target=self.loop,
                         args=(self.machine.commands, "command"))
        thread1 = Thread(target=self.loop,
                         args=(self.machine.unbuffered_commands, "unbuffered"))
        thread2 = Thread(target=self.eventloop,
                         args=(self.machine.sync_commands, "sync"))

        thread0.deamon = True
        thread1.deamon = True
        thread2.deamon = True

        thread0.start()
        thread1.start()
        thread2.start()

        self.machine.start()

        logging.info("Ertza ready")

    def loop(self, queue, name):
        pass

    def eventloop(self, queue, name):
        pass

    def exit(self):
        self.machine.exit()

        for f in self.machine.fans:
            f.set_value(0)

    def _config_thermistors(self):

        # Get available thermistors
        self.machine.thermistors = []
        th_p = 0
        while self.machine.config.has_option("thermistors", "port_TH%d" % th_p):
            adc_channel = self.machine.config.getint("thermistors",
                                                     "port_TH%d" % th_p)
            self.machine.thermistors.append(Thermistor(adc_channel,
                                                       "TH%d" % th_p))
            logging.debug(
                "Found thermistor TH%d at ADC channel %d" % (th_p, adc_channel))
            th_p += 1

    def _config_fans(self):

        self.machine.fans = None

        if self.machine.config.getboolean('fans', 'got_fans'):
            self.machine.fans = []
            f_p = 0
            while self.machine.config.has_option("fans", "address_F%d" % f_p):
                fan_channel = self.machine.config.getint("fans",
                                                         "address_F%d" % f_p)
                self.machine.fans.append(Fan(fan_channel))
                logging.debug(
                    "Found fan F%d at channel %d" % (f_p, fan_channel))
                f_p += 1

        for f in self.machine.fans:
            f.set_value(1)

        # Connect fans to thermistors
        if self.machine.fans and not NO_TH:
            self.machine.temperature_watchers = []
            for t, therm in enumerate(self.machine.thermistors):
                for f, fan in enumerate(self.machine.fans):
                    if self.machine.config.getboolean("temperature_watchers",
                                                      "connect_TH%d_to_F%d" %
                                                      (t, f),
                                                      fallback=False):
                        tw = TempWatcher(therm, fan,
                                         "TempWatcher-%d-%d" % (t, f))
                        tw.set_target_temperature(
                            self.machine.config.getfloat(
                                "thermistors", "target_temperature_TH%d" % t))
                        tw.set_max_temperature(
                            self.machine.config.getfloat(
                                "thermistors", "max_temperature_TH%d" % t))
                        tw.enable()
                        self.machine.temperature_watchers.append(tw)

    def _config_external_switches(self):

        # Create external switches
        self.machine.switches = []
        esw_p = 0
        while self.machine.config.has_option("switches",
                                             "keycode_ESW%d" % esw_p):
            esw_n = "ESW%d" % esw_p
            esw_kc = self.machine.config.getint("switches",
                                                "keycode_%s" % esw_n)
            name = self.machine.config.get("switches",
                                           "name_%s" % esw_n, fallback=esw_n)
            esw = Switch(esw_kc, name)
            esw.invert = self.machine.config.getboolean("switches",
                                                        "invert_%s " % esw_n)
            esw.function = self.machine.config.get("switches",
                                                   "function_%s " % esw_n)
            self.machine.switches.append(esw)
            logging.debug("Found switch %s at keycode %d" % (name, esw_kc))
            esw_p += 1

    def _config_leds(self):

        # Create leds
        self.machine.leds = []
        led_i = 0
        while self.machine.config.has_option("leds", "file_L%d" % led_i):
            led_n = "L%d" % led_i
            led_f = self.machine.config.get("leds", "file_%s" % led_n)
            led = Led(led_f)
            led_t = self.machine.config.get("leds", "trigger_%s" % led_n,
                                            fallback='none')
            led.set_trigger(led_t)
            if led_t is "timer":
                led.set_blink(self.machine.config.get("leds",
                                                      "blink_%s" % led_n,
                                                      fallback='500'))
            self.machine.leds.append(led)
            logging.debug("Found led %s, trigger: %s" % (led_n, led_t))
            led_i += 1


def main():
    e = Ertza()

    def signal_handler(signal, frame):
        e.exit()

    signal.signal(signal.SIGINT, signal_handler)

    e.start()

    signal.pause()


def profile():
    import yappi
    yappi.start()
    main()
    yappi.get_func_stats().print_all()

if __name__ == '__main__':
    _DEFAULT_CONF = '../conf/default.conf'
    _MACHINE_CONF = '../conf/machine.conf'
    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        profile()
    else:
        main()
