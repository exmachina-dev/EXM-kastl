#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""

from .types import MachineType
from .utils import get_machine_type

from .armaz import *
# from .wdy300 import *

def get_machine_class(mtype):
    if not isinstance(mtype, MachineType):
        raise TypeError('mtype must be a MachineType')

    return globals()[mtype.name]

