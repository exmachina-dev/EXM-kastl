# -*- coding: utf-8 -*-

from collections import namedtuple

_n = namedtuple('netdata', ['addr', 'fmt'])
_p = namedtuple('parameter', ['netdata', 'start', 'vtype', 'mode'])


_mfe100 = {
    'status':               _n(0, 'pad:24,bool,bool,bool,bool,'
                               'bool,bool,bool,bool'),
    'command':              _n(1, 'pad:18,bool,bool,bool,bool,bool,uint:1,uint:1,uint:3,'
                               'bool,bool,bool,bool'),
    'error_code':           _n(2, 'uint:32'),
    'jog':                  _n(3, 'float:32'),
    'torque_ref':           _n(4, 'float:32'),
    'velocity_ref':         _n(5, 'float:32'),
    'position_ref':         _n(6, 'float:32'),

    'torque_rise_time':     _n(10, 'float:32'),
    'torque_fall_time':     _n(11, 'float:32'),
    'acceleration':         _n(12, 'float:32'),
    'deceleration':         _n(13, 'float:32'),
    'entq_kp':              _n(14, 'float:32'),
    'entq_kp_vel':          _n(15, 'float:32'),
    'entq_ki':              _n(16, 'float:32'),
    'entq_kd':              _n(17, 'float:32'),

    'current':              _n(50, 'float:32'),
    'velocity':             _n(51, 'float:32'),
    'position':             _n(52, 'float:32'),
    'position_target':      _n(53, 'float:32'),
    'position_remaining':   _n(54, 'float:32'),
    'encoder_ticks':        _n(55, 'float:32'),
    'encoder_velocity':     _n(56, 'float:32'),
    'velocity_error':       _n(57, 'float:32'),
    'follow_error':         _n(58, 'float:32'),
    'torque':               _n(59, 'float:32'),
    'current_ratio':        _n(60, 'float:32'),
    'effort':               _n(61, 'float:32'),

    'drive_temp':           _n(62, 'float:32'),
    'dropped_frames':       _n(63, 'uint:32'),
}

MicroflexE100Map = {
    'status': {
        'drive_ready':      _p(_mfe100['status'], 7, bool, 'r'),
        'drive_enable':     _p(_mfe100['status'], 6, bool, 'r'),
        'drive_input':      _p(_mfe100['status'], 5, bool, 'r'),
        'motor_brake':      _p(_mfe100['status'], 4, bool, 'r'),
        'motor_temp':       _p(_mfe100['status'], 3, bool, 'r'),
        'timeout':          _p(_mfe100['status'], 2, bool, 'r'),
    },

    'command': {
        'enable':           _p(_mfe100['command'], 11, bool, 'w'),
        'cancel':           _p(_mfe100['command'], 10, bool, 'w'),
        'clear_errors':     _p(_mfe100['command'], 9, bool, 'w'),
        'reset':            _p(_mfe100['command'], 8, bool, 'w'),
        'control_mode':     _p(_mfe100['command'], 7, int, 'w'),
        'position_mode':    _p(_mfe100['command'], 6, int, 'w'),
        'move_mode':        _p(_mfe100['command'], 5, int, 'w'),
        'go':               _p(_mfe100['command'], 4, bool, 'w'),
        'set_home':         _p(_mfe100['command'], 3, bool, 'w'),
        'go_home':          _p(_mfe100['command'], 2, bool, 'w'),
        'stop':             _p(_mfe100['command'], 1, bool, 'w'),
        'timeout_enable':   _p(_mfe100['command'], 0, bool, 'w'),
    },

    'error_code':           _p(_mfe100['error_code'], 0, int, 'r'),
    'jog':                  _p(_mfe100['jog'], 0, float, 'rw'),
    'torque_ref':           _p(_mfe100['torque_ref'], 0, float, 'rw'),
    'velocity_ref':         _p(_mfe100['velocity_ref'], 0, float, 'rw'),
    'position_ref':         _p(_mfe100['position_ref'], 0, float, 'w'),
    'torque_rise_time':     _p(_mfe100['torque_rise_time'], 0, float, 'rw'),
    'torque_fall_time':     _p(_mfe100['torque_fall_time'], 0, float, 'rw'),
    'acceleration':         _p(_mfe100['acceleration'], 0, float, 'rw'),
    'deceleration':         _p(_mfe100['deceleration'], 0, float, 'rw'),
    'entq_kp':              _p(_mfe100['entq_kp'], 0, float, 'rw'),
    'entq_kp_vel':          _p(_mfe100['entq_kp_vel'], 0, float, 'rw'),
    'entq_ki':              _p(_mfe100['entq_ki'], 0, float, 'rw'),
    'entq_kd':              _p(_mfe100['entq_kd'], 0, float, 'rw'),

    'current':              _p(_mfe100['current'], 0, float, 'r'),
    'velocity':             _p(_mfe100['velocity'], 0, float, 'r'),
    'position':             _p(_mfe100['position'], 0, float, 'r'),
    'position_target':      _p(_mfe100['position_target'], 0, float, 'r'),
    'position_remaining':   _p(_mfe100['position_remaining'], 0, float, 'r'),
    'encoder_ticks':        _p(_mfe100['encoder_ticks'], 0, float, 'r'),
    'encoder_velocity':     _p(_mfe100['encoder_velocity'], 0, float, 'r'),
    'velocity_error':       _p(_mfe100['velocity_error'], 0, float, 'r'),
    'follow_error':         _p(_mfe100['follow_error'], 0, float, 'r'),
    'torque':               _p(_mfe100['torque'], 0, float, 'r'),
    'current_ratio':        _p(_mfe100['current_ratio'], 0, float, 'r'),
    'effort':               _p(_mfe100['effort'], 0, float, 'r'),

    'drive_temp':           _p(_mfe100['drive_temp'], 0, float, 'r'),
    'dropped_frames':       _p(_mfe100['dropped_frames'], 0, int, 'r'),
}
