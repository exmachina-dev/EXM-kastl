# -*- coding: utf-8 -*-

import logging
import os
import configparser

_VARIANT_PATH = "/etc/ertza/variants"


class ConfigParser(configparser.ConfigParser):
    """
    ConfigParser provides config interface. Its handle cascading config files.
    """

    def __init__(self, *args):
        self.variant_loaded = False
        self.variant = None

        super(ConfigParser, self).__init__(
            interpolation=configparser.ExtendedInterpolation())

        self.config_files = []
        for cfg in args[0:-1]:
            self.config_files.append(os.path.realpath(cfg))

        for cfg in self.config_files:
            if os.path.isfile(cfg):
                logging.info("Found " + cfg)
                self.read_file(open(cfg))
            else:
                logging.warn("Config file %s not found" % cfg)

    def load_variant(self, variant=None):
        """
        Load variant config file.

        If variant is not specified, load variant value defined in config file.
        """

        if self.variant_loaded:
            logging.warn("Variant already loaded: %s" % self.variant)
            return False
        if not variant:
            variant = self.get('machine', 'variant', fallback=False)
            if not variant:
                logging.warn("Couldn't get variant from config")
                return False

        variant_cfg = os.path.join(_VARIANT_PATH, variant + ".conf")
        if os.path.isfile(variant_cfg):
            logging.info("Loading variant config file: %s" % variant)
            variant_cfg = os.path.realpath(variant_cfg)
            self.config_files.append(variant_cfg)
            self.read_file(open(variant_cfg))
            self.variant_loaded = True
            self.variant = variant
        else:
            logging.warn("Couldn't find variant config file " + variant_cfg)

    def find_cape(self, partnumber):
        capes = self.get_cape_infos()
        for c in capes:
            if c['board_partnumber'] == partnumber:
                return c

    def get_cape_infos(self):
        capes = list()
        for addr in ('4', '5', '6', '7'):
            path = '/sys/bus/i2c/devices/2-005%d/eeprom' % addr
            if os.path.isfile(path):
                capes.append(self.get_eeprom_infos(path))
            else:
                continue

        return capes

    def get_eeprom_infos(self, eeprom):
        try:
            with open(eeprom, "rb") as f:
                data = f.read(88)
                infos = {
                    'eeprom_header': data[0:4],
                    'eeprom_rev': data[4:5],
                    'name': data[6:37].strip(),
                    'revision': data[38:41],
                    'manufacturer': data[42:57].strip(),
                    'partnumber': data[58:73].strip(),
                    'nb_pins_used': data[74:75],
                    'serialnumber': data[76:87],
                }
                return infos
        except IOError:
            pass
