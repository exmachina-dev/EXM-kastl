#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Benoit Rapidel <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""

from .types import MachineType


class AbstractMachineType(object):
    TYPE = MachineType.NONE

    def __init__(self, *args, **kwargs):
        pass
