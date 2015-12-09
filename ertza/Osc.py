# -*- coding: utf-8 -*-

from copy import copy


class OscPath(str):
    def __init__(self, path):
        self._p = path
        self.levels = self._p.split('/')

    def __repr__(self):
        return "%s" % '/'.join(self.levels)

    def __str__(self):
        return "%s" % '/'.join(self.levels)


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
                self.port = 6070
        else:
            raise AttributeError('Missing arguments for creation.')

    def __repr__(self):
        return "%s:%d" % (self.hostname, self.port)


class OscMessage(object):

    def __init__(self, path, args, **kwargs):
        self.path, self._args = OscPath(path), args
        self.sender, self.receiver = None, None

        if 'types' in kwargs:
            self.types = kwargs['types']

        if 'sender' in kwargs:
            self.sender = OscAddress(kwargs['sender'])
        if 'receiver' in kwargs:
            self.receiver = OscAddress(kwargs['receiver'])

        if 'msg_type' in kwargs:
            self.msg_type = kwargs['msg_type']

        self.answer = None
        self.protocol = 'OSC'

    @property
    def target(self):
        return self.path.split('/')[0:-2]

    @property
    def action(self):
        return self.path.split('/')[-1]

    @property
    def args(self):
        return self._args

    def __repr__(self):
        return '%s: %s %s' % (self.__class__.__name__, self.path,
                              ' '.join(iter(self.args)))
