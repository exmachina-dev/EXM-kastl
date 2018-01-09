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


def get_machine_type(str_type):
    str_type = ''.join([x.title() for x in str_type.split('.')])
    if str_type in MachineType.__members__:
        return getattr(MachineType, str_type)
    return MachineType.NONE
