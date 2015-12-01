# -*- coding: utf-8 -*-

import logging
import bitstring

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.register_read_message import (ReadHoldingRegistersRequest,
                                            ReadHoldingRegistersResponse)
from pymodbus.register_write_message import (WriteMultipleRegistersRequest,
                                             WriteMultipleRegistersResponse)
from pymodbus.other_message import (ReadWriteMultipleRegistersRequest,
                                    ReadWriteMultipleRegistersResponse,
                                    ExceptionResponse)
import pymodbus.exceptions as pmde


class ModbusBackend(object):
    min_netdata = 0
    max_netdata = 999
    register_nb_by_netdata = 2

    def __init(self, target_addr, target_port, target_nodeid):
        self.address = target_addr
        self.port = target_port
        self.nodeid = target_nodeid

        self._end = ModbusClient(host=self.address, port=self.port)

    def write_netdata(self, netdata, data, data_format):
        self._check_netdata(netdata)
        start = netdata * ModbusBackend.nb_reg_by_netdata

        data = bitstring.pack(data_format, *data)

        return self.wmr(start, data)

    def read_netdata(self, netdata, format):
        self._check_netdata(netdata)
        start = netdata * ModbusBackend.register_nb_by_netdata

        return self.rhr(start)

    def check_connectivity(self, **kwargs):
        status = self.get_status(force=True, **kwargs)
        if type(status) == dict:
            return True
        return False

    @staticmethod
    def to_int(bits, **kwargs):
        bits = bitstring.Bits(bin=bits)
        return bits.int

    @staticmethod
    def from_int(int_value, **kwargs):
        bits = bitstring.Bits(int=int_value, length=32)
        return bits.unpack('uintbe:16, uintbe')

    @staticmethod
    def to_float(bits, **kwargs):
        bits = bitstring.Bits(bin=bits)
        return bits.float

    @staticmethod
    def from_float(float_value, **kwargs):
        bits = bitstring.Bits(float=float_value, length=32)
        return bits.unpack('uintbe:16, uintbe')

    @staticmethod
    def to_bools(bits, **kwargs):
        bits = bitstring.Bits(bin=bits)
        l = list()
        for b in bits:
            l.append(b)

        return l

    @staticmethod
    def _from_bools(bools, **kwargs):
        bin_str = '0b'
        bools.reverse()
        for b in bools:
            if b is None:
                b = False
            bin_str += str(int(b))
        bits = bitstring.Bits(bin=bin_str)
        return bits.unpack('uintbe:16, uintbe')

    def _read_holding_registers(self, address):
        count = ModbusBackend.register_nb_by_netdata
        rq = ReadHoldingRegistersRequest(address, count,
                                         unit_id=self.node_id)
        return self._rq(rq)

    def _write_multiple_registers(self, address, value):
        rq = WriteMultipleRegistersRequest(address, value)

        return self._rq(rq)

    def _read_write_multiple_registers(self, address, value):
        rq = ReadWriteMultipleRegistersRequest(address, value,
                                               unit_id=self.node_id)
        return self._rq(rq)

    # Shortcuts
    rhr = _read_holding_registers
    wmr = _write_multiple_registers
    rwmr = _read_write_multiple_registers

    def _rq(self, rq, **kwargs):
        """
        Executes a Modbus request and return the response.
        """

        try:
            if not self.connected:
                logging.error("Unable to send request, not connected")
                return -1
            response = self._end.execute(rq)
            rpt = type(response)
            if rpt == ExceptionResponse:
                raise IOError('Exception received during execution.')
            elif rpt == WriteMultipleRegistersResponse:
                return True
            elif rpt == ReadHoldingRegistersResponse or \
                    rpt == ReadWriteMultipleRegistersResponse:
                regs = list()
                fmt = "{:0>16b}"
                for i in range(self.nb_reg_by_comms):
                    regs.append(fmt.format(response.getRegister(i)))
                return ''.join(regs)
        except pmde.ConnectionException:
            self.connected = False
            raise IOError('Unable to connect to slave')
