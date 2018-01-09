# -*- coding: utf-8 -*-


class AbstractDriver(object):

    def init_driver(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def exit(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError


class AbstractDriverError(Exception):
    pass


class AbstractTimeoutError(Exception):
    pass
