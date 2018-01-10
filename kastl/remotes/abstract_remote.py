#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Provides abstract remote, a base remote
"""

from threading import Event, Thread
from queue import Queue
import time

from ..filters import Filter


class AbstractRemote(object):
    """
    Represent a connected remote.
    """

    FEEDBACK_INTERVAL = 0.250
    HAS_FEEDBACK = False
    HAS_IP = False

    def __init__(self, *args, **kwargs):
        self.running_ev = Event()
        self.timeount_ev = Event()      # Timeout event when the remote
                                        # doesn't respond for more than timeout

        self.timeout = .5               # 500ms timeout by default
        self.request_timeout = 1.0

        self.remote_ip = None
        self.remote_port = None

        self.feedback_interval = self.FEEDBACK_INTERVAL

        self.messages_queue = Queue()

        self.filters = list()

        self._main_thread = None

        self.local_status = dict()

        # Order is important here because the handle will stop filtering in an
        # exclusive filter accepts the message
        self.register_filter(protocol=self.PROTOCOL, target=self.timeout_reset)

    def init_communication(self):
        raise NotImplementedError

    def start(self):
        if self._main_thread:
            raise RemoteError('Remote already started')

        self._main_thread = Thread(target=self.main_loop)
        self._main_thread.daemon = True
        self._main_thread.start()

    def connect(self):
        raise NotImplementedError

    def stop(self):
        self.running_ev.set()
        self._main_thread.join()

    def exit(self):
        self.stop()

    def main_loop(self, *args, **kwargs):
        raise NotImplementedError

    def handle(self, msg, **kwargs):
        """
        Filter a message coming from a processor, apply filters
        and decide what to do
        """

        for f in self.filters:
            if f.accepts(msg):
                f.handle(msg)
                if f.is_exclusive:
                    return

    def send_message(self, m):
        raise NotImplementedError

    def handle_config(self, m):
        raise NotImplementedError

    def handle_log(self, m):
        raise NotImplementedError

    def handle_motion(self, m):
        raise NotImplementedError

    def handle_remote(self, m):
        raise NotImplementedError

    def register_filter(self, new_filter=None, **kwargs):
        if new_filter:
            if not isinstance(new_filter, Filter):
                raise TypeError('Unexpected type %s for new_filter'
                                % type(new_filter))
        else:
            new_filter = Filter(**kwargs)

        self.filters.append(new_filter)

    def timeout_reset(self, m):
        self._last_message_time = time.time()

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

    @property
    def uid(self):
        raise NotImplementedError

    def __repr__(self):
        if self.HAS_IP:
            r = '{0.__class__.__name__}: {0.remote_ip}:{0.remote_port}'
        else:
            r = '{0.__class__.__name__}'

        return r.format(self)
