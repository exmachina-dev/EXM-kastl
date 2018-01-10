#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""

from enum import Enum, unique


@unique
class RemoteType(Enum):
    NONE = ''
    Varmo = 'SerialVarmo'
    Dario = 'OscDario'
