#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""

"""

from .abstract_machine import AbstractMachineError
from .abstract_machine import AbstractFatalMachineError


class MachineError(AbstractMachineError):
    pass


class FatalMachineError(AbstractFatalMachineError):
    pass


class MachineCommunicationTimeout(MachineError):
    pass
