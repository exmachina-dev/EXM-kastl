# -*- coding: utf-8 -*-

import logging
import bitstring
from threading import Event, Lock

from pylibmodbus import ModbusTcp as ModbusClient
from pylibmodbus import ModbusException

logging = logging.getLogger('kastl.drivers.modbus.backend')


class ModbusBackendError(Exception):
    pass


class ModbusCommunicationError(ModbusBackendError):
    _trigger = None
    _max_errors = 2
    _errors = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ModbusCommunicationError._errors += 1

        if self._errors >= self._max_errors:
            if self._trigger:
                self._trigger()
            logging.error('Max errors exceed: {}'.format(self._errors))
            ModbusCommunicationError._errors = 0


class ModbusBackend(object):
    min_netdata = 0
    max_netdata = 999
    register_nb_by_netdata = 2

    def __init__(self, target_addr, target_port, target_nodeid):
        ModbusCommunicationError._trigger = self.reconnect

        self.address = target_addr
        self.port = target_port
        self.nodeid = target_nodeid

        self.connected = False

        self._connecting = Event()
        self._reconnecting = Lock()
        self._end = ModbusClient(self.address, self.port)
        self._end.set_response_timeout(1)

    def connect(self):
        try:
            if self._connecting.is_set():
                logging.info('Connection in progress, skipping.')
                return

            self._connecting.set()
            res = self._end.connect()

            if res is None:
                self.connected = True
                return self.connected
        except ModbusException as e:
            logging.error('Unable to connect: {!r}'.format(e))
            raise ModbusBackendError(e)
            return False
        finally:
            self._connecting.clear()

    def close(self):
        self._end.close()
        self.connected = False

    def reconnect(self):
        if self._reconnecting.locked():
            logging.info('Reconnection in progress, skipping.')
            return
        with self._reconnecting:
            self.close()

            self._end = ModbusClient(self.address, self.port)
            self._end.set_response_timeout(1)
            self.connect()

    def write_netdata(self, netdata, data, data_format=None):
        self._check_netdata(netdata)
        start = netdata * self.register_nb_by_netdata

        if data_format:
            data = bitstring.pack(data_format, *data).unpack('uintbe:16,uintbe:16')
        else:
            data = bitstring.pack('uintbe:16,uintbe:16', *data)

        return self.wmr(start, data)

    def read_netdata(self, netdata, fmt):
        self._check_netdata(netdata)
        start = netdata * self.register_nb_by_netdata

        try:
            response = self.rhr(start)
            if response is None:
                raise ModbusCommunicationError('No data in response.')
            res = bitstring.pack('uintbe:16, uintbe:16', *response).unpack(fmt)
        except Exception as e:
            logging.error('Unexpected error: {!s}'.format(e))
            raise ModbusBackendError('Unexpected error: {!s}'.format(e))
        return res

    def _read_holding_registers(self, address):
        nb = self.register_nb_by_netdata
        rpt = self._analyze_response(self._end.read_registers, address, nb)
        return rpt

    def _write_multiple_registers(self, address, value):
        rpt = self._analyze_response(self._end.write_registers,
                                     address, value)

        return rpt

    def _read_write_multiple_registers(self, waddress, value, raddress):
        nb = self.register_nb_by_netdata
        rpt = self._analyze_response(self._end.write_and_read_registers,
                                     waddress, value, raddress, nb)
        return rpt

    def _check_netdata(self, netdata_address):
        if not (self.min_netdata <= netdata_address <= self.max_netdata):
            raise ValueError("Invalid netdata address: %d" % netdata_address)

    # Shortcuts
    rhr = _read_holding_registers
    wmr = _write_multiple_registers
    rwmr = _read_write_multiple_registers

    def _analyze_response(self, rq_func, *args, **kwargs):
        """
        Except an response and return the response or raise exceptions.
        """

        try:
            if not self.connected:
                logging.info("Not connected, connecting...")
                if not self.connect():
                    raise ModbusBackendError('Unable to connect.')

            rpt = rq_func(*args)
            return rpt
        except ModbusException as e:
            raise ModbusCommunicationError('Error while executing {}: {!s}'.format(rq_func, e))
