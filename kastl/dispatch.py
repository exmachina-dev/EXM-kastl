#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Communication dispatcher
"""

import logging
from threading import Event

from .async_utils import coroutine
from .exceptions import AbstractErtzaException, AbstractErtzaFatalException

logging = logging.getLogger('kastl.dispatch')


class DispatcherException(AbstractErtzaException):
    pass


class DispatcherFatalException(AbstractErtzaFatalException):
    pass


class Dispatcher(object):
    """
    Communication dispatcher
    """
    def __init__(self):
        self._processors = {}
        self._servers = {}

        self._running_event = Event()

    def add_server(self, server):
        if server.identifier in self._servers:
            raise DispatcherException('{} server already exists'.format(server.identifier))

        self._servers[server.identifier] = server

    def add_processor(self, proc):
        if proc.identifier in self._servers:
            raise DispatcherException('{} processor already exists'.format(proc.identifier))

        self._processors[proc.identifier] = proc

    def start(self):
        self._running_event.clear()

        for name, server in self._servers.items():
            logging.debug('Starting {} server'.format(name))
            server.start()
            logging.info('{} server started.'.format(name))

        for name, proc in self._processors.items():
            logging.debug('Starting {} processor'.format(name))
            proc.start()
            logging.info('{} processor started.'.format(name))

    def stop(self):
        self._running_event.set()

    def exit(self):
        self.stop()

        for name, server in self._servers.items():
            logging.info('Stopping {} server.'.format(name))
            server.exit()

    @coroutine
    def outlet(self, name):
        try:
            server = self._servers[name]
        except KeyError:
            raise DispatcherFatalException('Unable to find {} server'.format(name))

        while not self._running_event.is_set():
            try:
                message = (yield)

                server.send_message(message)
            except AbstractErtzaException as e:
                logging.error('Error while sending to {} server: {!s}'.format(name, e))
            except StopIteration:
                self._running_event.set()
                break

    @coroutine
    def inlet(self, name):
        try:
            proc = self._processors[name]
        except KeyError:
            raise DispatcherFatalException('Unable to find {} processor'.format(name))

        while not self._running_event.is_set():
            try:
                message = (yield)
                proc.execute(message)
            except AbstractErtzaException as e:
                logging.error(str(e))
            except StopIteration:
                self._running_event.set()
                break

    @property
    def processors(self):
        return self._processors

    @property
    def servers(self):
        return self._servers
