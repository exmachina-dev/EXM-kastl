Serial protocol
===============

The serial protocol implemented in ertza allow remote control through a serial link.

Serial parameters
-----------------

* Baudrate: **115200**
* Parity: **None**
* Stop bits: **1**

Protocol
--------

Each serial packet have a strict syntax.
The first 8 bytes are a constant fixed to :code:`ExmEisla`.
Next is two bytes defining the length of the packet.

The following 16 bytes defines the serial number of the sender.
For Eisla product range it is :code:`WWYYPPPPNNNN` where:

* :code:`WW` is the production week number in a ISO Format (1-53)
* :code:`YY` is the production year
* :code:`PPPP` is the part number (:code:`ARCP` for ArmazCape)
* :code:`NNNN` is the unit number produced during the week

Next is the command itself. The command is formed by:
Each part of a command is separated by a :code:`:`

* An alias
  It is a text string (encoded in ASCII) defining the desired action. Sub levels can be specified by adding a `.` between levels
  i.e. :code:`config.get`
* Zero or one or more argument
  Can be a string, an integer, a float or a boolean

Finally all commands ends with :code:`\r\n`

This give the following format: :code:`ExmEislaLLWWYYPPPPNNalias.level:parameter:parameter\r\n`

i.e.

    ``b'ExmEisla\x00\x370116ARCP0001config.get:machine.serialnumber\r\n'``

The length must be parsed by the receiver to ensure that the packet is not corrupted.

Data-types (WIP)
----------------
ExmEisla protocol does not provides a way to transmit data types along with data. Therefore, all devices must know what data type is expected.

For simplification, the following data types are recognized.

String
^^^^^^
Strings are ASCII encoded text.

Integer
^^^^^^^
Integers are signed 32-bit integers.


Float
^^^^^
Floats are encoded using `IEEE-754`_ using 32 bits.

.. _IEEE-754: https://en.wikipedia.org/wiki/IEEE_floating_point

Boolean
^^^^^^^
Boolean are encoded using 2 bits.
    ``b'\
