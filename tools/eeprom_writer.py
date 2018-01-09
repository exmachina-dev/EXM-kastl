#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import datetime
import struct
import bitstring as bs
from collections import OrderedDict


eeprom = '/sys/bus/i2c/devices/2-0054/eeprom'

available_variants = (
    'ARMAZ.HEAVY',
    'ARMAZ.FAST',
    'ARMAZ.FLAT',
    'ARMAZ.BOLD',
    'MOTIONSERVER',
)

pin_usage = OrderedDict()

#          U  D  S  R  UD PE MM
_unused = (0, 0, 0, 0, 0, 0, 0)
pin_usage['UART2_RXD'] = _unused
pin_usage['UART2_TXD'] = _unused
pin_usage['I2C1_SDA'] = _unused
pin_usage['I2C1_SCL'] = _unused
pin_usage['GPIO0_7'] = _unused
pin_usage['UART4_CTSN'] = _unused
pin_usage['UART4_RTSN'] = _unused
pin_usage['UART5_CTSN'] = _unused
pin_usage['UART5_RTSN'] = _unused
pin_usage['I2C2_SCL'] = (1, 2, 0, 1, 0, 0, 3,)
pin_usage['I2C2_SDA'] = (1, 3, 0, 1, 0, 0, 3,)
pin_usage['UART1_RXD'] = _unused
pin_usage['UART1_TXD'] = _unused
pin_usage['CLKOUT2'] = _unused
pin_usage['EHRPWM2A'] = _unused
pin_usage['EHRPWM2A'] = _unused
pin_usage['GPIO0_26'] = _unused
pin_usage['GPIO0_27'] = _unused
pin_usage['UART4_RXD'] = (1, 1, 0, 1, 1, 0, 6,)
pin_usage['UART4_TXD'] = _unused
pin_usage['GPIO1_0'] = _unused
pin_usage['GPIO1_1'] = _unused
pin_usage['GPIO1_2'] = _unused
pin_usage['GPIO1_3'] = _unused
pin_usage['GPIO1_4'] = _unused
pin_usage['GPIO1_5'] = _unused
pin_usage['GPIO1_6'] = _unused
pin_usage['GPIO1_7'] = _unused
pin_usage['GPIO1_12'] = _unused
pin_usage['GPIO1_13'] = _unused
pin_usage['GPIO1_14'] = _unused
pin_usage['GPIO1_15'] = _unused
pin_usage['GPIO1_16'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO1_17'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['EHRPWM1A'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['EHRPWM1B'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO1_28'] = (1, 2, 0, 0, 1, 0, 7,)
pin_usage['GPIO1_29'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO1_30'] = _unused
pin_usage['GPIO1_31'] = _unused
pin_usage['GPIO2_1'] = _unused
pin_usage['TIMER4'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['TIMER5'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['TIMER6'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['TIMER7'] = (1, 1, 0, 1, 0, 0, 7,)
pin_usage['GPIO2_6'] = _unused
pin_usage['GPIO2_7'] = _unused
pin_usage['GPIO2_8'] = _unused
pin_usage['GPIO2_9'] = _unused
pin_usage['GPIO2_10'] = _unused
pin_usage['GPIO2_11'] = _unused
pin_usage['GPIO2_12'] = _unused
pin_usage['GPIO2_13'] = _unused
pin_usage['UART5_TXD'] = (1, 2, 0, 0, 1, 0, 4,)
pin_usage['UART5_RXD'] = (1, 1, 0, 0, 0, 0, 4,)
pin_usage['UART3_CTSN'] = _unused
pin_usage['UART3_RTSN'] = _unused
pin_usage['GPIO2_22'] = _unused
pin_usage['GPIO2_23'] = _unused
pin_usage['GPIO2_24'] = _unused
pin_usage['GPIO2_25'] = _unused
pin_usage['SPI1_D0'] = (1, 1, 0, 1, 1, 0, 3,)
pin_usage['SPI1_D1'] = (1, 2, 0, 1, 1, 0, 3,)
pin_usage['SPI1_CS0'] = (1, 2, 0, 1, 1, 0, 3,)
pin_usage['GPIO3_19'] = (1, 1, 0, 1, 1, 0, 7,)
pin_usage['SPI1_SCLK'] = (1, 3, 0, 1, 1, 0, 3,)
pin_usage['GPIO3_21'] = _unused
pin_usage['AIN0'] = (1, 1, 0, 0, 0, 0, 0,)
pin_usage['AIN1'] = (1, 1, 0, 0, 0, 0, 0,)
pin_usage['AIN2'] = (1, 1, 0, 0, 0, 0, 0,)
pin_usage['AIN3'] = _unused
pin_usage['AIN4'] = _unused
pin_usage['AIN5'] = _unused

check_errors = 0

def check_dict(check_dict, orig_dict):
    check_errors = 0

    for key, value in check_dict.items():
        try:
            if value == orig_dict[key]:
                print('    {:<20}: {!s:<36}    Ok'.format(key, value))
            else:
                print('    {:<20}: {!s:<36}    Error: '
                      'original value {!s}'.format(key, value, orig_dict[key]))
                check_errors += 1
        except KeyError:
            print('    Unrecognized key: {}'.format(key))

    return check_errors


def serial_gen():
    isodate = datetime.date.today().isocalendar()
    yy = str(isodate[0])[2:]
    ww = str(isodate[1]).rjust(2, '0')
    asco = 'ARCP'
    print('Current date: W: {} Y: {}'.format(ww, yy))
    nnnn = input('Unit number manufactured in the current week (1-9999): ').rjust(4, '0')

    sn = ww + yy + asco + nnnn

    return sn

rev = input('Revision number (up to 4 chars) ? ')
if rev and len(rev) > 4:
    raise ValueError('Revision number is too long')

print('\nAvailable variants:')
for i, v in enumerate(available_variants):
    print('    [{}] {}'.format(i, v))
var_i = input('\nVariant (0..{}) ? '.format(len(available_variants)-1))

try:
    variant = available_variants[int(var_i)]
except KeyError:
    print('Invalid variant number. Exiting.')
    sys.exit()

data = OrderedDict()
data['eeprom_header'] = b'\xAA\x55\x33\xEE'
data['eeprom_rev'] = 'A1'.encode()
data['name'] = 'ArmazCape - Rev {}'.format(rev).ljust(32).encode()
data['revision'] = rev.rjust(4, '0').encode() if rev else '0000'.encode()
data['manufacturer'] = 'ExMachina'.ljust(16).encode()
data['partnumber'] = 'ARMAZCAPE'.ljust(16).encode()
data['nb_pins_used'] = struct.pack('>h', 92)
data['serialnumber'] = serial_gen().encode()

power_data = OrderedDict()
power_data['VDD_3V3B_current'] = struct.pack('>h', 400)
power_data['VDD_5V_current'] = struct.pack('>h', 400)
power_data['SYS_5V_current'] = struct.pack('>h', 0)
power_data['DC_supplied_current'] = struct.pack('>h', 2000)

custom_data = OrderedDict()
custom_data['variant'] = variant.ljust(16).encode()

with open(eeprom, 'wb') as e:
    print('Erasing existing data...', end='')
    e.write(b'\x00'*260)
    print(' Done.')

    e.seek(0)
    print('Writing cape data...', end='')
    for d in data.items():
        e.write(d[1])
    print(' Done.')

    pin_format = 'uint:1, uint:2, pad:6, uint:1, uint:1, uint:1, uint:1, uint:3'
    e.seek(88)
    print('Writing pins data...', end='')
    for p in pin_usage.items():
        if len(p[1]) != 7:
            print('Invalid pin config: {0}, {1}'.format(*p))
            continue

        p_b = bs.pack(pin_format, *p[1])
        e.write(p_b.bytes)
    print(' Done.')

    e.seek(236)
    print('Writing power data...', end='')
    for d in power_data.items():
        e.write(d[1])
    print(' Done.')

    e.seek(244)
    print('Writing custom data...', end='')
    for d in custom_data.items():
        e.write(d[1])
    print(' Done.')

with open(eeprom, 'rb') as e:
    print('Reading EEPROM...', end='')
    edata = e.read(260)
    print(' Done.')

    print('Checking EEPROM data...')
    pdata = {
        'eeprom_header': edata[0:4],
        'eeprom_rev': edata[4:6],
        'name': edata[6:38],
        'revision': edata[38:42],
        'manufacturer': edata[42:58],
        'partnumber': edata[58:74],
        'nb_pins_used': edata[74:76],
        'serialnumber': edata[76:88],
    }

    print('    * Checking cape data...')
    check_errors += check_dict(pdata, data)
    print('    Done.',)

    pdata = {
        'pin_data': edata[88:236],
    }
    pdata = {
        'VDD_3V3B_current': edata[236:238],
        'VDD_5V_current': edata[238:240],
        'SYS_5V_current': edata[240:242],
        'DC_supplied_current': edata[242:244],
    }

    print('    * Checking power data...')
    check_errors += check_dict(pdata, power_data)
    print('    Done.',)

    pdata = {
        'variant': edata[244:260],
    }
    print('    * Checking custom data...')
    check_errors += check_dict(pdata, custom_data)
    print('    Done.',)
    print('\nEEPROM check done.')

if check_errors != 0:
    print('{} errors while checking EEPROM. Check EEPROM write-protect.'.format(check_errors))
else:
    print('EEPROM check was successful.\n')

    if input('Clean commissioning packages (y/N): ') == 'y':
        import subprocess

        cmd = ['opkg', 'remove',]
        for pkg in ['armaz-commissioning-wizard', 'set-rtc-clock', 'emmc-flasher', 'kastl-eeprom',]:
            c_out = subprocess.check_output(cmd + [pkg,], universal_newlines=True).splitlines()
            print(*c_out, sep='\n')

    print('\nAll done.')
