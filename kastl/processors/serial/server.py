# -*- coding: utf-8 -*-

import logging
import time
import serial as sr
from threading import Thread

from .message import SerialMessage, SerialCommandString

logging = logging.getLogger('kastl.processors.serial.server')


class SerialServer(sr.Serial):

    def __init__(self, machine):
        self.machine = machine
        self.processor = self.machine.processors['Serial']

        dev = machine.config.get('serial', 'listen_device')
        if dev == 'None':
            dev = None
        baudrate = machine.config.getint('serial', 'baudrate', fallback=57600)

        logging.debug("Starting serial server on %s at %d" % (dev, baudrate))
        super().__init__(port=None, baudrate=baudrate)

        self.port = dev

        self.bytesize = sr.EIGHTBITS
        self.parity = sr.PARITY_NONE
        self.stopbits = sr.STOPBITS_ONE
        self.timeout = 0.5
        self.xonxoff = False
        self.rtscts = False

        self.rts = True
        self.dtr = True

        self.break_condition = False

        self.data_buffer = b''
        self.max_buffer_length = 256

        self.running = False
        self._last_read_time = time.time()

    def run(self):
        try:
            self.open()
        except sr.SerialException as e:
            self.running = False
            logging.error(e)

        while self.running:
            try:
                # read all that is there or wait for one byte
                data = self.read(self.inWaiting() or 1)
                if time.time() > (self._last_read_time + self.timeout):     # Empty buffer if data is older than timeout
                    self.data_buffer = b''

                self._last_read_time = time.time()
                self.data_buffer += (data)
                self.limit_buffer_length()
                self.find_serial_packets()

            except sr.SerialException as e:
                logging.error(str(e))
            except Exception as e:
                logging.error(str(e))

    def start(self):
        self.running = True

        self._t = Thread(target=self.run)
        self._t.daemon = True
        self._t.start()

        self.send_announce()

    def send_announce(self):
        m = SerialMessage()
        m.cmd_bytes['data'] = 'announce'
        self.send_message(m)

    def send_alive(self):
        m = SerialMessage()
        m.cmd_bytes['data'] = 'alive'
        self.send_message(m)

    def send_message(self, message):
        if not self.running:
            logging.error('Serial port is not opened. Aborting.')
            return

        if message.msg_type is not 'log':
            logging.debug("Sending: %s %s" % (message, message.tobytes))
        self.write(message.tobytes)
        self.flush()

    def close(self):
        logging.debug("Closing serial server")
        self.running = False
        self._t.join()

    def exit(self):
        self.close()

    def limit_buffer_length(self):
        if len(self.data_buffer) > self.max_buffer_length:
            pos = self.data_buffer.rfind(SerialCommandString.CmdEnd)
            if pos >= 0:
                discarded_data, self.data_buffer = self.data_buffer[:pos+2], \
                    self.data_buffer[pos+2:]
                logging.error('Data buffer too long. {} bytes discarded.'
                              .format(len(discarded_data)))

    def find_serial_packets(self):
        pos = self.data_buffer.find(SerialCommandString.CmdEnd)
        if pos >= 0:
            packet, self.data_buffer = self.data_buffer[:pos+2], \
                self.data_buffer[pos+2:]
            m = SerialMessage(cmd_bytes=packet)
            self.processor.enqueue(m)
            self.find_serial_packets()
