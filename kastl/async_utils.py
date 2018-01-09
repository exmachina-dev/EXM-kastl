# -*- coding: utf-8 -*-

from inspect import isgenerator
from threading import Lock


def coroutine(func):
    def wrapper(*args, **kwargs):
        generator = func(*args, **kwargs)
        next(generator)
        return generator
    return wrapper


class Channel(object):
    _Channels = {}
    _Lock = Lock()

    def __init__(self, name):
        if name in self._Channels:
            raise ValueError('Name already exists')

        self._name = name
        with self._Lock:
            self._Channels[self.name] = {
                'ids': [],
                'coros': {},
            }

    def suscribe(self, coro):
        if not isgenerator(coro):
            raise ValueError('Invalid coroutine specified')

        if id(coro) in self.coro_ids:
            raise ValueError('Coroutine already subscribed.')

        with self._Lock:
            self.coro_ids.append(id(coro))
            self.coros[id(coro)] = coro

    def unsuscribe(self, coro):
        if not isgenerator(coro):
            raise ValueError('Invalid coroutine specified')

        with self._Lock:
            if id(coro) not in self.coro_ids:
                raise ValueError('Coroutine not found.')

            self.coro_ids.remove(id(coro))
            self.coros.pop(id(coro))

    def send(self, message):
        with self._Lock:
            coros = list(self.coros.values())

        for coro in coros:
            try:
                coro.send(message)
            except StopIteration:
                raise

    def close(self, end_message):
        pass

    @property
    def name(self):
        return self._name

    @property
    def coro_ids(self):
        return self._Channels[self.name]['ids']

    @property
    def coros(self):
        return self._Channels[self.name]['coros']
