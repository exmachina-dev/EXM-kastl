#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
Provides remotes objects
"""

from .exceptions import RemoteError, FatalRemoteError, RemoteTimeoutError
from .types import RemoteType

from .abstract_remote import AbstractRemote
from .osc_remotes import OscDarioRemote
from .serial_remotes import SerialVarmoRemote

def get_remote_class(remote_type):
    try:
        return globals()[remote_type.value + 'Remote']
    except KeyError:
        return None
