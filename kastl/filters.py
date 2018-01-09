#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Message filters

Filters are used to dispatch incoming messages
"""

import logging

logging = logging.getLogger('kastl.filter')


class Filter(object):
    def __init__(self, *args, **kwargs):
        self.is_exclusive = kwargs.pop('exclusive', False)

        if 'target' in kwargs and 'targets' in kwargs:
            raise ValueError('target and targets kwargs are mutually exclusive.')
        self.targets = kwargs.pop('targets', tuple())
        target = kwargs.pop('target', None)
        if target:
            self.targets = (target,)

        # Filter kwargs
        self.protocol = kwargs.pop('protocol', '').upper()
        self.alias_mask = kwargs.pop('alias_mask', None)
        self.args_length = kwargs.pop('args_length', None)
        self.sender = kwargs.pop('sender', None)

    def accepts(self, message):
        """
            For a filter to accept a message,
            the message must fulfill all conditions.
        """
        if self.protocol and \
                message.protocol.upper() != self.protocol:
            return False
        if self.alias_mask and \
                not message.command.startswith(self.alias_mask):
            return False
        if self.args_length is not None and \
                len(message.args) != self.args_length:
            return False
        if self.sender is not None and \
                message.sender.hostname != self.sender:
            return False

        return True

    def handle(self, m):
        if self.targets:
            for t in self.targets:
                t(m)

    def __str__(self):
        return str(repr(self))

    def __repr__(self):
        spec = (self.protocol, self.alias_mask, self.args_length, self.sender)
        filters = ' '.join([str(x) for x in spec])
        return '%s: %s' % (self.__class__.__name__, filters)

