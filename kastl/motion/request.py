#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""


from threading import Event


class MotionRequest(object):
    """
    Hold a motion request issued by a remote or a motion unit.
    """

    TYPES = {
        'velocity': float,
        'acceleration': float,
        'deceleration': float,
    }

    def __init__(self, request_type, *args, **kwargs):
        if request_type not in self.TYPES:
            raise ValueError('No request type named %s', request_type)

        self.done_ev = Event()
        self.result = None
        self.args = args

    def set_done(self, result=None):
        if result is not None:
            self.result = result

        self.done_ev.set()

    @property
    def done(self):
        return self.done_ev.is_set()

