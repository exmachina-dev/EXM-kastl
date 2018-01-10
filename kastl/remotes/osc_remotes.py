#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
OSC remotes
"""

from .exceptions import RemoteError, RemoteTimeoutError
from ..motion.exceptions import MotionError
from .abstract_remote import AbstractRemote
from ..processors.osc import OscMessage
from ..motion.request import MotionRequest

import logging


logging = logging.getLogger('kastl.remotes.serial')


class OscRemote(AbstractRemote):
    PROTOCOL = "Osc"
    HAS_IP = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.remote_ip = kwargs.get('ip', None)
        self.remote_port = kwargs.get('port', None)
        if self.remote_port is not None:
            self.remote_port = int(self.remote_port)

    def send(self, *args, **kwargs):
        msg = kwargs['msg'] if 'msg' in kwargs else \
            self.message(*args, hostname=self.remote_ip, port=self.remote_port)

        return self.send_message(msg)

    def message(self, *args, **kwargs):
        return OscMessage(*args, **kwargs)


class OscDarioRemote(OscRemote):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.register_filter(protocol=self.PROTOCOL, target=self.handle_config,
                             alias_mask='/config/', exclusive=True)
        self.register_filter(protocol=self.PROTOCOL, target=self.handle_log,
                             alias_mask='/log/', exclusive=True)
        self.register_filter(protocol=self.PROTOCOL, target=self.handle_motion,
                             alias_mask='/motion/', exclusive=True)
        self.register_filter(protocol=self.PROTOCOL, target=self.handle_remote,
                             alias_mask='/remote/', exclusive=True)

    def main_loop(self, *args, **kwargs):
        while not self.running_ev.is_set():
            self.running_ev.wait(self.feedback_interval)

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
        try:
            k, a, = m.args
            nk = k.decode()
            if nk.startswith('machine.'):
                nk = nk[7:] # Strip machine. from key

            if nk in MotionRequest.TYPES:
                mr = MotionRequest(nk, *a)
                self.command_queue.put(mr)
                mr.done_ev.wait(self.request_timeout)
                if mr.done:
                    self.reply_ok(m, k, *a)
                else:
                    e = MotionError('Timeout while setting %s to %s' %
                                            str(k), ', '.join([str(sa) for si in a]))
                    self.reply_error(m, k, e)
                    raise e
            else:
                print(k, a)
        except Exception as e:
            logging.exception(e)

    def handle_remote(self, m):
        if m.path.endswith('/connect'):
            self.reply_ok(m)

    @property
    def uid(self):
        return self.__class__.__name__
