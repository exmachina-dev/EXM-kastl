#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""

from .abstract_type import AbstractMachineType
from .types import MachineType

class ArmazHeavy(AbstractMachineType):
    TYPE = MachineType.ArmazHeavy

class ArmazFast(AbstractMachineType):
    TYPE = MachineType.ArmazFast

class ArmazFlat(AbstractMachineType):
    TYPE = MachineType.ArmazFlat
