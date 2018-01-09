#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim: fenc=utf-8 shiftwidth=4 softtabstop=4
#
# Copyright © 2017 Benoit Rapidel, ExMachina <benoit.rapidel+devs@exmachina.fr>
#
# Distributed under terms of the GPLv3+ license.

"""
OSC remotes
"""

from .abstract_remote import AbstractRemote


class OscRemote(AbstractRemote):
    pass


class OscGuiRemote(OscRemote):
    pass

