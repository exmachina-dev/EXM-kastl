# -*- coding: utf-8 -*-

import uuid
from copy import copy
from liblo import Message as OMessage

from ..abstract_message import AbstractMessage


class OscPath(str):
    SEP = '/'

    def __init__(self, path):
        self._p = path
        self.levels = self._p.split(self.SEP)

    def __repr__(self):
        return "%s" % self.SEP.join(self.levels)

    def __str__(self):
        return "%s" % self.SEP.join(self.levels)


class OscAddress(object):
    def __init__(self, address_object=None, **kwargs):
        if address_object:
            self.hostname = copy(address_object.hostname)
            self.port = int(copy(address_object.port))

            del(address_object)
        elif 'hostname' in kwargs:
            self.hostname = kwargs['hostname']

            if 'port' in kwargs:
                self.port = kwargs['port']
            else:
                self.port = 6970
        else:
            raise AttributeError('Missing arguments for creation.')

    def __repr__(self):
        return "%s:%d" % (self.hostname, self.port)


class OscMessage(AbstractMessage):
    SEP = '/'
    protocol = 'OSC'

    def __init__(self, path, *args, **kwargs):
        super().__init__(**kwargs)

        self.path, self._args = OscPath(path), args
        self._args = [str(a) if isinstance(a, Exception) else a for a in self._args]

        self.types = kwargs['types'] if 'types' in kwargs else None

        if self.types and len(self.types) != len(self._args):
            raise TypeError('Lenght of args and types must match')


        s = kwargs.get('sender', None)
        self.sender = OscAddress(s) if s else None
        r = kwargs.get('receiver', None)
        self.receiver = OscAddress(r) if r else None

        if not (self.sender or self.receiver):
            self.receiver = OscAddress(**kwargs)


    @property
    def command(self):
        return str(self.path)

    @property
    def args(self):
        return tuple(self._args)

    def to_message(self):
        if self.types:
            a = []
            for i in zip(self.types, self.args):
                a.append(i)
            return OMessage(self.path, *a)
        m = OMessage(self.path, *self.args)
        return m

    @property
    def message(self):
        return self.to_message()

    @property
    def uid(self):
        try:
            uid = self.args[0]
            try:
                uid = uuid.UUID(uid)
            except ValueError:
                return False
            return uid
        except IndexError:
            return False

    def __add__(self, value):
        self._args.append(value)

        return self
