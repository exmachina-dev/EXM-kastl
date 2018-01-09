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

from ..filters import Filter


class AbstractRemote(object):
    """
    Represent a connected remote.
    """

    INTERVAL = 0.250

    def __init__(self, *args, **kwargs):
        self.running_ev = Event()
        self.timeount_ev = Event()      # Timeout event when the remote
                                        # doesn't respond for more than timeout

        self.timeout = .5               # 500ms timeout by default
        self.request_timeout = 1.0

        self.messages_queue = Queue()

        self.filters = list()

        self._main_thread = None

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

    def register_filter(self, new_filter=None, **kwargs):
        if new_filter:
            if not isinstance(new_filter, Filter):
                raise TypeError('Unexpected type %s for new_filter'
                                % type(new_filter))
        else:
            new_filter = Filter(**kwargs)

        self.filters.append(new_filter)

    @property
    def uid(self):
        raise NotImplementedError
