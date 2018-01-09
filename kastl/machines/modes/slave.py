# -*- coding: utf-8 -*-

import logging

from .standalone import StandaloneMachineMode

logging = logging.getLogger('kastl.machine.modes.slave')


class SlaveMachineMode(StandaloneMachineMode):
    _param = StandaloneMachineMode._param

    StandaloneMachineMode.MachineMap.update({
        'master':           _param(str, 'r'),
        'master_port':           _param(str, 'r'),
    })

    DirectAttributesGet = StandaloneMachineMode.DirectAttributesGet + (
        'master',
        'master_port',
    )
