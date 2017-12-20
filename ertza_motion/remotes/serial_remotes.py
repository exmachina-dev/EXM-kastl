#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Serial remotes
"""

from .abstract_remote import AbstractRemote
from ..processors.serial import SerialMessage

import logging


logging = logging.getLogger('ertza.remotes.serial')


class SerialRemote(AbstractRemote):
    PROTOCOL = 'Serial'
    HAS_IP = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.local_status = dict()

        self.register_filter(protocol=self.PROTOCOL, target=self.handle_get,
                             alias_mask='machine.get', args_length=1,
                             exclusive=True)
        self.register_filter(protocol=self.PROTOCOL, target=self.handle_set,
                             alias_mask='machine.set',
                             exclusive=True)

    def start(self):
        pass

    def reply_ok(self, msg, *args, **kwargs):
        self.reply(msg, *args, add_path='ok', **kwargs)

    def reply_error(self, msg, *args, **kwargs):
        self.reply(msg, *args, add_path='error', **kwargs)

    def reply(self, msg, *args, **kwargs):
        ap = kwargs.pop('add_path', None)
        if ap:
            if not isinstance(ap, str):
                raise TypeError('add_path kwarg must be a string')

            full_path = msg.command + ap \
                if ap.startswith(msg.SEP) \
                else '{0.command}{0.SEP}{1}'.format(msg, ap)
        else:
            full_path = self.command

        self.send(full_path, *args, **kwargs)

    def send(self, *args, **kwargs):
        msg = kwargs['msg'] if 'msg' in kwargs else \
            self.message()

        for d in args:
            msg.cmd_bytes += d

        return self.send_message(msg)

    def message(self, *args, **kwargs):
        return SerialMessage(*args, **kwargs)

    @property
    def uid(self):
        return self.__class__.__name__

    def handle_get(self, m):
        k = m.args[0].decode()

        try:
            v = self.local_status[k]
            if callable(v):
                v = v()
            self.reply_ok(m, k, v)
        except KeyError:
            self.reply_error(m, k, 'No value for key.')

    def handle_set(self, m):
        k, a, = m.args

        print(k, a)
        self.reply_ok(m, k, *a)


class SerialVarmoRemote(SerialRemote):
    HAS_FEEDBACK = False
    REFRESH_INTERVAL = 1.0
