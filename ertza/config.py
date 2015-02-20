# -*- coding: utf-8 -*-

from ertza.base import BaseWorker, BaseResponse, BaseRequest
import ertza.errors as err

import time
import os

import configparser

user_config_path = os.path.expanduser('~/.ertza')
_DEFAULTS = {
        'log': {
            'log_path': os.path.join(user_config_path, 'logs'),
            },
        'osc': {
            'server_port': 7900,
            'client_port': 7901,
            },
        'modbus': {
            'device': '192.168.100.2',
            'node_id' : 2,
            'port': 502,
            },
        }

_CONFPATH = [
        '/etc/ertza/default.conf',
        os.path.join(user_config_path, 'ertza.conf'),
        ]


class BaseConfigParser(configparser.ConfigParser):
    """
    BaseConfigParser provides some helpers function for
    configparser.ConfigParser.

    Helps sharing a simple config manager accross different processes.
    """

    def __init__(self):
        self._conf_path = _CONFPATH
        self.save_path = self._conf_path[-1]
        self.autosave = True

        super(BaseConfigParser, self).__init__(
                interpolation=configparser.ExtendedInterpolation()
        )

    def set(self, section, option, value=None):
        super(BaseConfigParser, self).set(section, option, value)
        if self.autosave:
            self.save()

        return super(BaseConfigParser, self).get(section, option)

    def read_configs(self, path=None):
        # Don't auto save when reading config
        asave = self.autosave
        self.autosave = False

        if path and os.path.exists(path):
            path = os.path.expanduser(path)
            if path in self._conf_path:
                raise ValueError('%s is already present.' % path)
            self._conf_path.append(path)

        try:
            rtn = self.read(self._conf_path)
            missing = set(self._conf_path) - set(rtn)
            if missing == set(self._conf_path):
                raise configparser.ParsingError('No config file found.')
        except configparser.ParsingError as e:
            self.read_hard_defaults()
            self.save()
            raise e

        # Restore previous self.autosave state
        self.autosave = asave
        return list(missing)

    def read_hard_defaults(self):
        return self.read_dict(_DEFAULTS)

    @property
    def configs(self):
        return self._conf_path

    def save(self):
        with open(self.save_path, 'w') as configfile:
            super(BaseConfigParser, self).write(configfile)

    def dump(self, section=None):
        output = ''
        for s, o in self.items():
            output += ('[ %s : ( ' % s)
            for o, v in o.items():
                output += ('%s: %s — ' % (o, v))
            output += (']')

        return output


ConfigParser = BaseConfigParser


class ConfigRequest(BaseRequest):
    def _check_args(self, *args):
        self.args = args
        if self.args:
            self.method = None
            self.value = None

    def get(self, *args):
        self._check_args(*args)
        self.method = self._methods['get']
        rp = self.send()
        return rp.value

    def set(self, *args):
        self._check_args(*args)
        self.method = self._methods['set']
        return self.send().value

    def dump(self, *args):
        self._check_args(*args)
        self.method = self._methods['dump']
        return self.send().value


class ConfigResponse(BaseResponse):
    def __init__(self, target, request, config=None, *args):
        super(ConfigResponse, self).__init__(target, *args)
        self.request = request
        self._config = config

    def get_from_config(self, *args):
        self.method = self._methods['get']

        if not self._config:
            raise ValueError("Config isn't defined.")
        if len(args) == 3:
            section, option, fallback = args
            self.value = self._config.get(section, option, fallback=fallback)
        elif len(args) == 2:
            section, option = args
            self.value = self._config.get(section, option)

    def set_to_config(self, *args):
        self.method = self._methods['set']

        if not self._config:
            raise ValueError("Config isn't defined.")
        if len(args) == 3:
            section, option, value = args
        else:
            raise ValueError("One or more argument is missing.")
        self.value = self._config.set(str(section), str(option), str(value))

    def dump_config(self, *args):
        self.method = self._methods['dump']

        if not self._config:
            raise ValueError("Config isn't defined.")
        if len(args) == 1:
            section, = args
        else:
            section = None
        self.value = self._config.dump(str(section))

    def handle(self):
        args = self.request.args
        if self.request.method == self._methods['set']:
            self.set_to_config(*args)
        elif self.request.method == self._methods['get']:
            self.get_from_config(*args)
        elif self.request.method == self._methods['dump']:
            self.dump_config(*args)
        else:
            raise ValueError('Unexcepted method: %s', self.request.method)

        return self.value


class ConfigWorker(BaseWorker):
    """
    Master process that handle configuration.
    """

    _config = ConfigParser

    def __init__(self, sm):
        super(ConfigWorker, self).__init__(sm)
        self.log_pipe = self.initializer.cnf_log_pipe[0]
        self.rmt_pipe = self.initializer.cnf_rmt_pipe[0]
        self.osc_pipe = self.initializer.cnf_osc_pipe[0]
        self.mdb_pipe = self.initializer.cnf_mdb_pipe[0]
        self.pipes = self.log_pipe, self.rmt_pipe, self.osc_pipe, self.mdb_pipe

        self.interval = 0.001

        self._config = self._config()

        self.get_logger()

        self.watched_options = {
                'osc': {
                    'server_port': None
                    },
                }

        try:
            self.lg.debug('Reading configs: %s', self._config.configs)
            missing = self._config.read_configs()
            self.lg.info('Missing configs: %s', missing)
        except configparser.Error as e:
            error = err.ConfigError(e.message)
            self.lg.warn(error)
            raise error

        self.run()

    def run(self):
        self._watchconfig(init=True)
        self.config_event.set()
        while not self.exit_event.is_set():
            for pipe in self.pipes:
                if pipe.poll():
                    rq = pipe.recv()
                    self.lg.debug(rq)
                    if not type(rq) is ConfigRequest:
                        raise ValueError('Unexcepted type: %s' % type(rq))
                    rs = ConfigResponse(pipe, rq, self._config)
                    rs.handle()
                    self.lg.debug(rs)
                    rs.send()

            self._watchconfig()

            time.sleep(self.interval)

    def _watchconfig(self, init=None):
        for s, o in self.watched_options.items():
            for o, v in o.items():
                try:
                    if self._config[s][o] is not v:
                        if not init:
                            if s is 'osc' and o is 'server_port':
                                self.lg.debug("""
Server port as changed. Old port: %s. New port: %s
Triggering OSC event.
                                """, v, self._config[s][o])
                                self.osc_event.set()
                        self.watched_options[s][o] = self._config[s][o]
                except configparser.Error as e:
                    self.lg.debug(repr(e))


__all__ = ['ConfigRequest', 'ConfigResponse', 'ConfigWorker', 'ConfigParser']

if __name__ == '__main__':
    cf = ConfigParser()
    cf.read_configs()
    print(cf.configs)
    print('Config:')
    print(cf.dump())
