# -*- coding: utf-8 -*-

import logging
import os
from glob import glob
import struct
import configparser
from configparser import Error, NoSectionError, NoOptionError, ParsingError
import itertools
from collections import ChainMap, namedtuple, OrderedDict

logger = logging.getLogger('kastl.config')

_VARIANT_PATH = "/etc/kastl/variants"
_PROFILE_PATH = "/etc/kastl/profiles"
_PROFILE_OPTIONS = {
    'machine': {
        'ip_address': ('str', None),
        'operating_mode': ('str', None),
    },
    'motor': {
        'acceleration': ('float', 'm.s-1'),
        'deceleration': ('float', 'm.s-1'),
        'control_mode': ('int', None),

        'entq_kp': ('float', None),

        'entq_kp_vel': ('float', None),
        'entq_ki': ('float', None),
        'entq_kd': ('float', None),
        'torque_rise_time': ('float', 'ms'),
        'torque_fall_time': ('float', 'ms'),

        'application_coefficient': ('float', None),
        'application_velocity_unit': ('str', None),
        'application_position_unit': ('str', None),

        'invert': ('bool', None),

        'acceleration_time_mode': ('bool', None),

        'custom_max_velocity': ('float', None),

        'custom_max_acceleration': ('float', None),
        'custom_max_deceleration': ('float', None),
        'custom_max_position': ('float', None),
        'custom_min_position': ('float', None),
    }
}

__all__ = ['NoSectionError', 'NoOptionError', 'ParsingError', 'ConfigParserError',
           'FileNotFoundError', 'VariantError', 'ProfileError', 'ConfigParser']

parameter = namedtuple('parameter', ['vtype', 'unit', 'value'])


class ConfigParserError(Error):
    pass


class FileNotFoundError(ConfigParserError):
    """
    Raised when a config file cannot be found or read.
    """
    pass


class VariantError(ConfigParserError):
    """
    Raised when an error happens during a variant operation.
    """
    pass


class ProfileError(ConfigParserError):
    """
    Raised when an error happens during a profile operation.
    """

    pass


class _ChainMap(ChainMap):
    def get(self, key, default=None, **kwargs):
        try:
            if default is not None:
                kwargs['fallback'] = default
            return super().get(key, default=kwargs['fallback'])
        except KeyError:
            return super().get(key)

class MultiOrderedDict(OrderedDict):
    def __setitem__(self, key, value):
        if key.endswith('[]'):
            if key in self:
                self[key].append(value)
            else:
                super().__setitem__(key, [value,])
        else:
            super().__setitem__(key, value)

class TupleInterpolation(configparser.ExtendedInterpolation):
    def before_get(self, parser, section, option, value, defaults):
        if option.endswith('[]'):
            L = []
            for v in value:
                L.append(super().before_get(parser, section, option, ''.join(v), defaults))
            return L
        else:
            return super().before_get(parser, section, option, value, defaults)


class AbstractConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        kwargs['strict'] = False
        kwargs['dict_type'] = MultiOrderedDict
        super().__init__(interpolation=TupleInterpolation(),
                         **kwargs)

        self.config_files = []
        if args and not isinstance(args, (tuple, list)):
            args = (args,)

        for cfg in args:
            real_path_cfg = os.path.realpath(cfg)
            if os.path.isfile(real_path_cfg):
                self.config_files.append(real_path_cfg)
                logger.debug("Found " + cfg)
                try:
                    self.read_file(open(real_path_cfg))
                    logger.info("Parsed " + cfg)
                except ParsingError:
                    logger.warn("Unable to parse config file %s" % real_path_cfg)
            else:
                logger.warn("Config file %s not found" % real_path_cfg)

        self._config_proxies = [None, None]

    def save(self, nfile=None):
        """
        Save config into a config file.
        """

        save_to = nfile or self.config_files[-1]

        if os.path.isfile(save_to):
            logger.info('{} already existing, overwriting'.format(save_to))

        if len(self.config_files) > 1:
            tmp_config = self - AbstractConfigParser(self.config_files[0:-1])
        else:
            tmp_config = self

        with open(save_to, 'w') as sfile:
            tmp_config.write(sfile)

    def dump(self):
        dump = {}
        for sec, opts in self.items():
            for opt, val in opts.items():
                dump.update({(sec, opt): val})

        return dump

    def get(self, section, option, **kwargs):
        if self._config_proxies:
            for p in self._config_proxies:
                if p is None or section not in p or option not in p[section]:
                    continue

                return p[section][option]

        return super().get(section, option, **kwargs)

    def __getitem__(self, key):
        if self._config_proxies:
            for p in self._config_proxies:
                if p is None or key not in p:
                    continue

                if p[key] is None:
                    continue

                return p[key]

            return super().__getitem__(key)
        else:
            return super().__getitem__(key)

    def _join_multiline_values(self):
        defaults = self.default_section, self._defaults
        all_sections = itertools.chain((defaults,),
                                       self._sections.items())
        for section, options in all_sections:
            for name, val in options.items():
                if not name.endswith('[]'):
                    if isinstance(val, list):
                        val = '\n'.join(val).rstrip()
                    options[name] = self._interpolation.before_read(self,
                                                                    section,
                                                                    name, val)

    def __contains__(self, key):
        """ Don't check DEFAULT section. """
        return self.has_section(key)

    def __len__(self):
        """ Don't count DEFAULT section. """
        return self._sections

    def __iter__(self):
        """ Don't fetch DEFAULT section. """

        return iter(self._sections)

    def __sub__(self, other):
        tmp_conf = AbstractConfigParser()
        for sec, opts in self.items():
            if other.has_section(sec):
                for opt, value in opts.items():
                    if opt not in other[sec]:
                        if sec not in tmp_conf:
                            tmp_conf.add_section(sec)
                        tmp_conf[sec][opt] = value
            else:
                tmp_conf[sec] = opts

        return tmp_conf


class ProxyConfigParser(AbstractConfigParser):
    def __init__(self, path, name, **kwargs):
        if not isinstance(name, str):
            raise TypeError('Name must be a string')

        self._name = name
        if path is None and kwargs.get('basedir', None):
            self._basedir = str(kwargs['basedir'])
        else:
            self._basedir = os.path.dirname(path)

        super().__init__(path)

    @property
    def name(self):
        return self._name

    @name.setter
    def _set_name(self, name):
        self._name = name
        self.config_files[-1] = '{}/{}.conf'.format(self._basedir, name)


class ConfigParser(AbstractConfigParser):
    """
    ConfigParser provides config interface. Its handle cascading config files.
    """

    VARIANT_PRIORITY = 0
    PROFILE_PRIORITY = 1

    PROFILE_OPTIONS = _PROFILE_OPTIONS

    def __init__(self, *args, **kwargs):
        self.config_dir = kwargs.pop('config_dir', None)
        if not self.config_dir:
            self.config_dir = '/etc/kastl'

        afiles = []
        for cf in args:
            af = self.config_dir + '/' + cf if \
                not (cf.startswith('/') and
                     cf.startswith('./') and
                     cf.startswith('../')) else cf
            afiles.append(af)

        super().__init__(*afiles, **kwargs)

    def load_config(self, config_file):
        """
        Load config file appending to *config_files*.

        :param config_file: The config file to load
        :raises FileNotFoundError: if file doesn't exist
        """
        if not os.path.isfile(config_file):
            raise FileNotFoundError

        logger.info("Loading config file: %s" % config_file)
        config_file = os.path.realpath(config_file)
        self.config_files.append(config_file)
        self.read_file(open(config_file))
        return True

    def load_variant(self, variant=None, **kwargs):
        """
        Load a variant config file.

        If variant is not specified, load variant value defined in config file.

        :param str variant: The variant config file to load
        :raises VariantError: if a variant is already loaded
        """

        if self.variant:
            logger.warn("Variant already loaded: %s" % self.variant.name)
            raise VariantError('Variant already loaded')

        if not variant:
            cape_infos = self.find_cape()
            if cape_infos:
                try:
                    variant = cape_infos['variant'].lower()
                except Exception as e:
                    logger.warn('Got exception while decoding eeprom: {!s}'.format(e))
            if not variant:
                logger.warn("Couldn't get variant from eeprom")
                variant = self.get('server', 'variant', fallback=False)

            if not variant:
                logger.warn("Couldn't get variant from eeprom or config")
                return False

        try:
            variant_path = kwargs.get('variant_path', None)

            if variant_path:
                variant_config_file = os.path.join(variant_path, variant + ".conf")
            else:
                variant_config_file = os.path.join(_VARIANT_PATH, variant + ".conf")

            self._config_proxies[self.VARIANT_PRIORITY] = ProxyConfigParser(variant_config_file, variant)

            logger.info("Loaded variant config file: %s" % variant)
        except ParsingError as e:
            logger.warn("Couldn't parse variant file {0} : {1!s}" % (variant_config_file, e))

    def load_profile(self, profile=None, **kwargs):
        """
        Load profile file.

        If *profile* is not specified, load profile defined in config file with ``server:profile``.
        Store the loaded profile in config.

        :param str profile: The profile file to load
        :raises ProfileError: if no profile is given and server:profile doesn't exist in config
        """

        if not profile:
            try:
                profile = self['server']['profile']
            except KeyError:
                raise ProfileError('No profile specified in config and none provided.')

        try:
            profile_path = kwargs.get('profile_path', None)

            if profile_path:
                profile_config_path = os.path.join(profile_path, profile + ".conf")
            else:
                profile_config_path = os.path.join(_PROFILE_PATH, profile + ".conf")

            self._config_proxies[self.PROFILE_PRIORITY] = ProxyConfigParser(profile_config_path, profile)
            self['server']['profile'] = profile
        except ParsingError as e:
            logger.warn("Couldn't load profile file {0}: {1!s}" % (self.profile_config_path, e))

    def unload_profile(self):
        try:
            del self['server']['profile']
            del self._config_proxies[self.PROFILE_PRIORITY]
        except (IndexError, NoSectionError, NoOptionError):
            pass

    def dump_profile(self, profile=None):
        if not self.get('server', 'profile', fallback=profile):
            raise ProfileError('No profile loaded or provided')

        if profile:
            profile_path = '{}/{}.conf'.format(_PROFILE_PATH, profile)
            profile_config = ProxyConfigParser(profile_path, profile)
            return profile_config.dump()
        else:
            return self.profile_config.dump()

    def get_profile_options(self):
        return self.PROFILE_OPTIONS

    def save_profile(self, profile=None):
        if self.profile is None:
            raise ProfileError('No profile loaded')

        if profile:
            self.profile.save('{}/{}.conf'.format(_PROFILE_PATH, profile))
        else:
            self.profile.save()

    def get_profiles_list(self):
        files = glob('{}/*.conf'.format(_PROFILE_PATH))
        profiles = []
        for f in files:
            profiles.append(f.replace(_PROFILE_PATH + '/', '')[0:len('.conf') * -1])

        return profiles

    def profile_set(self, sec, opt, value):
        if not self.profile.has_section(sec):
            self.profile.add_section(sec)
        self.profile[sec][opt] = value

    def find_cape(self, partnumber='ARMAZCAPE'):
        capes = self.get_cape_infos()
        for c in capes:
            if not c:
                continue
            if c['partnumber'] == partnumber:
                return c

    def get_cape_infos(self):
        capes = list()
        for addr in range(4, 7):
            path = '/sys/bus/i2c/devices/2-005%d/eeprom' % addr
            if os.path.isfile(path):
                capes.append(self.get_eeprom_infos(path))
            else:
                continue

        return capes

    def get_eeprom_infos(self, eeprom):
        try:
            with open(eeprom, "rb") as f:
                data = f.read(260)
                try:
                    infos = {
                        'eeprom_header': data[0:4],
                        'eeprom_rev': data[4:6].decode(),
                        'name': data[6:38].strip().decode(),
                        'revision': data[38:42].decode(),
                        'manufacturer': data[42:58].strip().decode(),
                        'partnumber': data[58:74].strip().decode(),
                        'nb_pins_used': struct.unpack('>h', data[74:76])[0],
                        'serialnumber': data[76:88].decode(),
                        'variant': data[244:260].strip().decode(),
                    }
                    return infos
                except UnicodeDecodeError as e:
                    logger.error('Error while decoding eeprom: {!s}'.format(e))
                    return False
        except IOError as e:
            logger.error('Error while reading eeprom: {!s}'.format(e))
            return False

    @property
    def variant(self):
        try:
            return self._config_proxies[self.VARIANT_PRIORITY]
        except IndexError:
            return None

    @property
    def profile(self):
        try:
            return self._config_proxies[self.PROFILE_PRIORITY]
        except IndexError:
            self._config_proxies[self.PROFILE_PRIORITY] = ProxyConfigParser(None, '', basedir=_PROFILE_PATH)
            return self._config_proxies[self.PROFILE_PRIORITY]

    def __getitem__(self, key):
        childs_sec = []
        for cfp in self._config_proxies:
            if cfp is not None and key in cfp:
                childs_sec.append(cfp[key])

        if key in self._proxies:
            childs_sec.append(self._proxies[key])

        if len(childs_sec) == 0:
            raise KeyError

        return _ChainMap(*childs_sec)
