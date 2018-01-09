#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Main class for kastl

import logging as lg
import os
import os.path
import sys
import signal
from threading import Thread
from multiprocessing import JoinableQueue
import queue

from .configparser import ConfigParser, ProfileError
from .motion import MotionUnit, MotionError

from .processors import OscProcessor, SerialProcessor

from .processors.osc.server import OscServer
from .processors.serial.server import SerialServer
from .processors.serial.message import SerialCommandString

from .pwm import PWM
from .thermistor import Thermistor

from .fan import Fan
from .switch import Switch
from .tempwatcher import TempWatcher
from .led import Led

from .network_utils import EthernetInterface

version = "2.1.0~Motion"

_DEFAULT_CONF = "default.conf"
_MACHINE_CONF = "machine.conf"
_CUSTOM_CONF = "custom.conf"

console_logger = lg.StreamHandler()
console_formatter = lg.Formatter('%(asctime)s %(name)-27s '
                                 '%(levelname)-8s %(message)s',
                                 datefmt='%H:%M:%S')

logger = lg.getLogger('kastl')
logger.addHandler(console_logger)
console_logger.setFormatter(console_formatter)


class Kastl(object):
    """
    Main class for kastl.

    Handle log, configuration, startup and dispatch others tasks to
    various processes
    """

    def __init__(self, *agrs, **kwargs):
        """ Init """
        logger.info("Kastl initializing. Version: " + version)

        self.motion_unit = MotionUnit()
        self.mu.version = version

        custom_conf = kwargs.pop('config', None)
        if not custom_conf:
            custom_conf = _CUSTOM_CONF

        logger.info('Custom file: %s' % custom_conf)

        self.mu.config = ConfigParser(_DEFAULT_CONF,
                                      _MACHINE_CONF,
                                      custom_conf,
                                      **kwargs)

        if not os.path.isfile(self.mu.config.config_files[0]):
            logger.error('%s does not exist, exiting.', self.mu.config.config_files[0])
            sys.exit(1)

        self._config_leds()
        for l in self.mu.leds:
            if l.function == 'status':
                l.set_blink(500)
            if l.function == 'error':
                l.on()

        # Get loglevel from config file
        level = int(self.mu.config.get('system', 'loglevel', fallback=10))
        if level > 0:
            lg.getLogger('').setLevel(level)
            logger.setLevel(level)
            logger.info("Log level set to %d" % level)

        self.mu.cape_infos = self.mu.config.find_cape('ARMAZCAPE')

        if self.mu.cape_infos:
            name = self.mu.cape_infos['name']
            logger.info('Found cape %s with S/N %s' % (name, self.mu.serialnumber))
        SerialCommandString.SerialNumber = self.mu.serialnumber

        try:
            self.mu.config.load_profile()
        except ProfileError as e:
            logger.info('Unable to load profile: {!s}'.format(e))

        try:
            i = self.mu.config.get('server', 'interface', fallback='eth0')
            logger.info('Configuring {} interface'.format(i))
            eth = None
            try:
                eth = EthernetInterface(i)
                logger.info('Setting interface {} to up'.format(i))
                eth.link_up()
                logger.info('Setting up default route'.format(i))
                eth.add_route('default')
            except Exception as e:
                logger.error(e)

            ip = self.mu.config.get('server', 'ip_address', fallback=None)
            if eth:
                try:
                    if not ip:
                        ip = '10'
                        for byte in eth.mac_address.split(':')[3:6]:
                            ip += '.{}'.format(int('0x{}'.format(byte), base=0))
                        ip += '/8'

                    logger.info('Adding ip {} to {}'.format(ip, i))
                    eth.add_ip(ip)
                except Exception as e:
                    logger.error(e)
            else:
                logger.warn('Specified interface is not available: {}'.format(i))
            self.mu.ethernet_interface = eth
        except IndexError:
            logger.warn('No IP address found')

        self._config_external_switches()
        self._config_thermistors()
        self._config_fans()

        # Create queue of commands
        self.mu.commands = JoinableQueue(20)

        if not self.mu.config.get('osc', 'disable', fallback=False):
            self.mu.processors['OSC'] = OscProcessor(self.mu)
            self.mu.comms['OSC'] = OscServer(self.mu)

        if not self.mu.config.get('serial', 'disable', fallback=False):
            self.mu.processors['Serial'] = SerialProcessor(self.mu)
            self.mu.comms['Serial'] = SerialServer(self.mu)

    def start(self):
        """ Start the processes """
        self.running = True

        # Start the processes
        commands_thread = Thread(target=self.loop,
                                 args=(self.mu.commands, "command"))

        commands_thread.deamon = True
        commands_thread.start()

        for name, comm in self.mu.comms.items():
            comm.start()
            logger.info("%s communication module started" % name)

        self.mu.start()

        for l in self.mu.leds:
            if l.function == 'status':
                l.set_blink(50)
            elif l.function == 'error':
                l.off()

        for name, comm in self.mu.comms.items():
            comm.send_alive()
            logger.info("Sending alive message with %s communication module" % name)

        logger.info("Kastl ready")

    def loop(self, message_queue, name):
        """ When a new message comes in, dispatch it """

        try:
            while self.running:
                try:
                    message = message_queue.get(block=True, timeout=1)
                except queue.Empty:
                    continue

                try:
                    p = self.mu.processors[message.protocol]
                except KeyError:
                    raise KeyError('Unable to get %s processor' % message.protocol)

                try:
                    self.mu.handle(message)
                finally:
                    message_queue.task_done()
        except Exception as e:
            logger.exception("Exception in %s loop: %s" % (name, e))

    def exit(self):
        logger.info('Stopping motion unit')
        self.mu.stop()

        self.running = False

        for f in self.mu.fans:
            f.set_value(0)

        for l in self.mu.leds:
            if l.function == 'status':
                l.off()
            elif l.function == 'error':
                l.off()

        logger.info('Exited.')

    @property
    def mu(self):
        return self.motion_unit

    def _config_thermistors(self):

        # Get available thermistors
        self.mu.thermistors = []

        if self.mu.config.getboolean('thermistors', 'got_thermistors'):
            th_p = 0

            while self.mu.config.has_option("thermistors",
                                                 "port_TH%d" % th_p):
                try:
                    adc_channel = self.mu.config.getint("thermistors",
                                                            "port_TH%d" % th_p)
                    therm = Thermistor(adc_channel, 'TH{}'.format(th_p))
                    self.mu.thermistors.append(therm)
                    logger.debug('Found thermistor TH{} '
                                'at ADC channel {}'.format(th_p, adc_channel))
                    th_p += 1
                except Exception as e:
                    logger.warn('Unable to configure thermistor TH{}: {!s}'.format(th_p, e))

    def _config_fans(self):
        self.mu.fans = []

        # Get available fans
        if self.mu.config.getboolean('fans', 'got_fans'):
            PWM.set_frequency(1560)

            f_p = 0
            while self.mu.config.has_option("fans", "address_F%d" % f_p):
                try:
                    fan_channel = self.mu.config.getint("fans",
                                                            "address_F%d" % f_p)
                    fan = Fan(fan_channel)
                    fan.min_speed = float(self.mu.config.get(
                        "fans", 'min_speed_F{}'.format(f_p), fallback=0.0))
                    fan.set_value(1)
                    self.mu.fans.append(fan)
                    logger.debug(
                        "Found fan F%d at channel %d" % (f_p, fan_channel))
                    f_p += 1
                except Exception as e:
                    logger.warn('Unable to configure fan F{}: {!s}'.format(f_p, e))

        th_cf = self.mu.config["thermistors"]
        tw_cf = self.mu.config["temperature_watchers"]

        # Connect fans to thermistors
        if self.mu.fans:
            self.mu.temperature_watchers = []

            for t, therm in enumerate(self.mu.thermistors):
                for f, fan in enumerate(self.mu.fans):
                    if tw_cf.get("connect_TH{}_to_F{}".format(t, f),
                                 fallback=False):
                        tw = TempWatcher(therm, fan,
                                         "TempWatcher-{}-{}".format(t, f))
                        tw.set_target_temperature(float(
                            th_cf.get("target_temperature_TH%d" % t)))
                        tw.set_max_temperature(float(
                            th_cf.get("max_temperature_TH%d" % t)))
                        tw.interval = float(th_cf.get('update_interval_TH{}'.format(t),
                                                      fallback=5))
                        tw.enable()
                        self.mu.temperature_watchers.append(tw)
        elif self.mu.thermistors:
            self.mu.temperature_watchers = []
            for t, therm in enumerate(self.mu.thermistors):
                tw = TempWatcher(therm, None, "TempLogger-%d" % t)
                tw.set_max_temperature(float(
                    th_cf.get("max_temperature_TH%d" % t)))
                tw.interval = float(th_cf.get('update_interval_TH{}'.format(t),
                                              fallback=5))
                tw.enable(mode=False)
                self.mu.temperature_watchers.append(tw)

    def _config_external_switches(self):
        Switch.callback = self.mu.switch_callback

        # Create external switches
        self.mu.switches = []
        esw_p = 0
        if self.mu.config.getboolean('switches', 'got_switches', fallback=True):
            while self.mu.config.has_option("switches",
                                                "keycode_ESW%d" % esw_p):
                esw_n = "ESW%d" % esw_p
                esw_kc = self.mu.config.getint("switches",
                                                    "keycode_%s" % esw_n)
                name = self.mu.config.get("switches",
                                            "name_%s" % esw_n, fallback=esw_n)
                esw = Switch(esw_kc, name)
                esw.invert = self.mu.config.getboolean("switches",
                                                            "invert_%s" % esw_n)
                esw.function = self.mu.config.get("switches",
                                                    "function_%s" % esw_n)
                self.mu.switches.append(esw)
                logger.debug("Found switch %s at keycode %d" % (name, esw_kc))
                esw_p += 1

    def _config_leds(self):

        # Create leds
        self.mu.leds = []
        if self.mu.config.getboolean('leds', 'got_leds'):
            led_i = 0
            while self.mu.config.has_option("leds", "file_L%d" % led_i):
                led_n = "L%d" % led_i
                led_f = self.mu.config.get("leds", "file_%s" % led_n)
                led_fn = self.mu.config.get("leds", "function_%s" % led_n,
                                                 fallback=None)
                led = Led(led_f, led_fn)
                led_t = self.mu.config.get("leds", "trigger_%s" % led_n,
                                                fallback='none')
                led.set_trigger(led_t)
                if led_t == "timer":
                    led.set_blink(self.mu.config.get("leds",
                                                          "blink_%s" % led_n,
                                                          fallback='500'))
                self.mu.leds.append(led)
                logger.debug("Found led %s, trigger: %s" % (led_n, led_t))
                led_i += 1


def main(parent_args=None):
    import argparse

    parser = argparse.ArgumentParser(prog='kastl')
    parser.add_argument('--config', type=str, help='use CONFIG as custom config file')
    parser.add_argument('--config-dir', type=str, help='use CONFIG_DIR as base config directory')

    if parent_args:
        args, args_remaining = parser.parse_known_args(parent_args)
    else:
        args, args_remaining = parser.parse_known_args()

    k = Kastl(**vars(args))

    def signal_handler(signal, frame):
        k.exit()

    signal.signal(signal.SIGINT, signal_handler)

    k.start()

    signal.pause()


def profile():
    import yappi
    yappi.start()
    main()
    yappi.get_func_stats().print_all()

if __name__ == '__main__':
    _DEFAULT_CONF = '../conf/default.conf'
    _MACHINE_CONF = '../conf/fake.conf'
    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        profile()
    else:
        main()
