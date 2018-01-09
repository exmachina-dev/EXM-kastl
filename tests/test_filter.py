#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""

import pytest
from functools import partial

from kastl.motion.filters import Filter
from kastl.processors.osc.message import OscMessage, OscAddress


class Test_Filter(object):
    def setup_class(self):
        self.filters = list()
        self.filters.append(Filter(protocol='Osc'))
        self.filters.append(Filter(protocol='Serial'))
        self.filters.append(Filter(alias_mask='/test_mask'))
        self.filters.append(Filter(alias_mask='/another_mask'))
        self.filters.append(Filter(args_length=2))
        self.filters.append(Filter(args_length=3))
        self.filters.append(Filter(sender='127.0.0.1'))
        self.filters.append(Filter(sender='127.0.0.2'))

        self.results = dict()

        for f in self.filters:
            f.targets = (partial(self.cb, self, f),)
            self.results[f] = None

    def test_protocol(self):
        msg = self.message('/empty')
        self.send(msg)

        assert self.results[self.filters[0]] == msg
        assert self.results[self.filters[1]] == None

    def test_mask(self):
        msg = self.message('/test_mask')
        self.send(msg)

        assert self.results[self.filters[2]] == msg
        assert self.results[self.filters[3]] == None

        self.reset_results()
        msg = self.message('/another_mask')
        self.send(msg)

        assert self.results[self.filters[2]] == None
        assert self.results[self.filters[3]] == msg

    def test_args_length(self):
        msg = self.message('/test_mask', 'args1')
        self.send(msg)

        assert self.results[self.filters[4]] == None
        assert self.results[self.filters[5]] == None

        self.reset_results()
        msg = self.message('/test_mask', 'args1', 2)
        self.send(msg)

        assert self.results[self.filters[4]] == msg
        assert self.results[self.filters[5]] == None

        self.reset_results()
        msg = self.message('/test_mask', 'args1', 2, 5.5)
        self.send(msg)

        assert self.results[self.filters[4]] == None
        assert self.results[self.filters[5]] == msg

    def test_sender(self):
        self.reset_results()
        msg = self.message('/empty', 'args1', sender='127.0.0.2')
        self.send(msg)

        assert self.results[self.filters[6]] == None
        assert self.results[self.filters[7]] == msg

        self.reset_results()
        msg = self.message('/empty', 'args1')
        self.send(msg)

        assert self.results[self.filters[6]] == msg
        assert self.results[self.filters[7]] == None

    def message(self, *args, **kwargs):
        s = kwargs.pop('sender', '127.0.0.1')
        msg = OscMessage(*args, hostname='127.0.0.1', **kwargs)
        msg.sender = OscAddress(hostname=s)
        return msg

    def send(self, msg):
        for f in self.filters:
            if f.accepts(msg):
                f.handle(msg, None)

    def cb(self, name, msg):
        self.results[name] = msg

    def reset_results(self):
        for k in self.results.keys():
            self.results[k] = None
