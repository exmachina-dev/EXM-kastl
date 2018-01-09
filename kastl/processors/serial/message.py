# -*- coding: utf-8 -*-

import logging

import bitstring as bs
from collections import namedtuple

from ..abstract_message import AbstractMessage


logging = logging.getLogger('kastl.serial.message')

SerialCommandStruct = namedtuple('SerialCommandStruct', ('protocol', 'length', 'serial_number', 'data', 'end'))


class SerialCommandString(object):
    CmdFormat = 'bits:64,bits:16,bits:96,bits,bits:16'
    CmdEnd = b'\r\n'
    CmdSep = b':'

    IntLength = 32
    FloatLength = 32
    StringLength = 15

    SerialNumber = '000000000000'

    def __init__(self, cmd_bytes=None, **kwargs):
        if cmd_bytes:
            self._b = bs.pack('bits', cmd_bytes)
            self._c = SerialCommandStruct(*[b.bytes for b in self._b.unpack(self.CmdFormat)])
        else:
            self._c = SerialCommandStruct(b'', b'\x00\x00', b'', b'', b'')
            self['serial_number'] = self.SerialNumber.encode()
            self['end'] = self.CmdEnd
            self['protocol'] = kwargs['protocol'] if 'protocol' in kwargs \
                else b'ExmEisla'

    @property
    def tobytes(self):
        command_len = len(bs.pack(self.CmdFormat, *self._c).tobytes())
        self['length'] = bs.pack('uint:16', command_len).tobytes()

        return bs.pack(self.CmdFormat, *self._c).tobytes()

    @property
    def command(self):
        return self['data'].split(self.CmdSep)[0]

    @property
    def args(self):
        return tuple(self['data'].split(self.CmdSep, maxsplit=2)[1:])

    @property
    def length(self):
        return bs.Bits(self['length']).uint

    def _pack(self, value):
        if value is None:
            raise ValueError('''value can't be None''')

        if isinstance(value, str):
            if self['data'] != b'' and len(value) > self.StringLength:
                mid = int(self.StringLength / 2) - 3
                value = value[0:mid+2] + '...' + value[-mid-1:]
            value = value.encode()
        elif isinstance(value, bool):
            value = bs.Bits(uintle=value, length=8).tobytes()
        elif isinstance(value, int):
            value = bs.Bits(intle=value, length=self.IntLength).tobytes()
        elif isinstance(value, float):
            value = bs.Bits(floatle=value, length=self.FloatLength).tobytes()

        return value

    def __getitem__(self, key):
        return getattr(self._c, key)

    def __setitem__(self, key, value):
        value = self._pack(value)

        self._c = self._c._replace(**{key: value})

    def __add__(self, value):
        value = self._pack(value)

        if self['data'] != b'':
            self['data'] += self.CmdSep + value
        else:
            self['data'] = value
        return self

    def __len__(self):
        return len(self.tobytes)

    def __repr__(self):
        return '{0[protocol]} {0[serial_number]} {0.length} {0[data]}'.format(self)

    def __str__(self):
        return '{0[protocol]} {0[serial_number]} {0.length} {0[data]}'.format(self)


class SerialTarget(object):
    def __init__(self, **kwargs):
        if 'unitid' in kwargs:
            self.unitid = kwargs['unitid']
        else:
            raise AttributeError('Missing arguments for creation.')

    def __repr__(self):
        return "%s" % self.unitid


class SerialMessage(AbstractMessage):
    SEP = '.'
    protocol = 'Serial'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cmd_bytes = SerialCommandString(cmd_bytes=kwargs['cmd_bytes']) \
            if 'cmd_bytes' in kwargs else SerialCommandString()


    @property
    def command(self):
        return self.cmd_bytes.command.decode()

    @property
    def args(self):
        return self.cmd_bytes.args

    @property
    def serial_number(self):
        return self.cmd_bytes['serial_number']

    @property
    def length(self):
        return self.cmd_bytes.length

    @property
    def tobytes(self):
        return self.cmd_bytes.tobytes

    def __len__(self):
        return len(self.cmd_bytes)

    def __add__(self, value):
        self.cmd_bytes += value

        return self
