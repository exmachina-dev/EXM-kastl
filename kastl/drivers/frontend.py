# -*- coding: utf-8 -*-

from collections import namedtuple

_UNSET = object()

_PARAM = namedtuple('parameter', ['vtype', 'fallback'])


class DriverFrontend(object):
    _frontend_keys = {
        # Gearbox
        'gearbox_input_coefficient':    _PARAM(float, 1),
        'gearbox_output_coefficient':   _PARAM(float, 1),

        # Motor and drive constants
        'torque_constant':              _PARAM(float, 1),   # in Nm/A
        'drive_rated_current':          _PARAM(float, 1),   # in A

        # Limits
        'max_velocity':                 _PARAM(float, 1),   # in rpm (motor side)
        'max_acceleration':             _PARAM(float, 1),
        'max_deceleration':             _PARAM(float, 1),

        'min_torque_rise_time':         _PARAM(float, 5000),
        'min_torque_fall_time':         _PARAM(float, 5000),

        # Default values
        'acceleration':                 _PARAM(float, 1),
        'deceleration':                 _PARAM(float, 1),

        'control_mode':                 _PARAM(int, 2),

        # Enhanced torque mode PID values
        'entq_kp':                      _PARAM(float, 1.15),
        'entq_kp_vel':                  _PARAM(float, 1),
        'entq_ki':                      _PARAM(float, 0.1),
        'entq_kd':                      _PARAM(float, 5),

        'torque_rise_time':             _PARAM(float, 5000),
        'torque_fall_time':             _PARAM(float, 5000),

        # Application parameters
        'application_coefficient':      _PARAM(float, 1),
        'invert':                       _PARAM(bool, False),
        'acceleration_time_mode':       _PARAM(bool, False),

        'custom_max_velocity':          _PARAM(float, _UNSET),  # in rpm (application side)
        'custom_max_acceleration':      _PARAM(float, _UNSET),
        'custom_max_deceleration':      _PARAM(float, _UNSET),

        'custom_max_position':          _PARAM(float, _UNSET),
        'custom_min_position':          _PARAM(float, _UNSET),

        # Units
    }

    _invert_keys = ('torque_ref', 'velocity_ref', 'position_ref')
    _gearbox_keys = ('torque_ref', 'velocity_ref', 'position_ref',
                     'acceleration', 'deceleration',
                     'position', 'position_target', 'position_remaining',
                     'torque', 'velocity')
    _application_keys = ('torque_ref', 'velocity_ref', 'position_ref',
                         'acceleration', 'deceleration',
                         'position', 'position_target', 'position_remaining')

    DEFAULTS_KEYS = ('acceleration', 'deceleration', 'torque_rise_time', 'torque_fall_time',
                     'entq_kp', 'entq_kp_vel', 'entq_ki', 'entq_kd')

    def load_config(self, config, section='motor'):
        self.frontend_config = config
        self.frontend_section = section

    @property
    def gearbox_ratio(self):
        return self.gearbox_input_coefficient / self.gearbox_output_coefficient

    def _output_value_limit(self, key, value):
        if 'acceleration' == key:
            return value if value < self.max_acceleration else self.max_acceleration
        elif 'deceleration' == key:
            return value if value < self.max_deceleration else self.max_deceleration
        elif 'torque_rise_time' == key:
            return value if value > self.min_torque_rise_time else self.min_torque_rise_time
        elif 'torque_fall_time' == key:
            return value if value > self.min_torque_fall_time else self.min_torque_fall_time
        elif 'velocity_ref' == key:
            value = value if value < self.max_velocity else self.max_velocity
            value = value if value > -self.max_velocity else -self.max_velocity

        return value

    def _output_value_coefficient(self, key, value):
        if key in self._invert_keys:
            value = value * -1 if self.invert else value

        if key == 'velocity_ref' and self.custom_max_velocity is not _UNSET:
            value = value if value < self.custom_max_velocity else self.custom_max_velocity
            value = value if value > -self.custom_max_velocity else -self.custom_max_velocity
        elif key == 'position_ref':
            if self.custom_max_position is not _UNSET:
                value = value if value < self.custom_max_position else self.custom_max_position
            if self.custom_min_position is not _UNSET:
                value = value if value > self.custom_min_position else self.custom_min_position
        elif key == 'acceleration' and self.custom_max_acceleration is not _UNSET:
            value = value if value < self.custom_max_acceleration else self.custom_max_acceleration
        elif key == 'deceleration' and self.custom_max_deceleration is not _UNSET:
            value = value if value < self.custom_max_deceleration else self.custom_max_deceleration
        elif key == 'torque_ref':
            value /= self.torque_constant
            value /= self.drive_rated_current
            value *= 100

        if key in self._gearbox_keys:
            value /= self.gearbox_ratio
        if key in self._application_keys:
            value *= self.application_coefficient

        if key in ('acceleration', 'deceleration') and self.acceleration_time_mode:
            value = (self.max_velocity / self.gearbox_ratio * self.application_coefficient) / value

        return value

    def output_value(self, key, value):
        return self._output_value_limit(key, self._output_value_coefficient(key, value))

    def _input_value_coefficient(self, key, value):
        if key in self._gearbox_keys:
            value *= self.gearbox_ratio

        if key in self._application_keys:
            value /= self.application_coefficient

        if key in ('acceleration', 'deceleration') and self.acceleration_time_mode:
            value = (self.max_velocity / self.gearbox_ratio * self.application_coefficient) / value
        elif key == 'torque_ref':
            value /= 100
            value *= self.drive_rated_current
            value *= self.torque_constant

        if key in self._invert_keys:
            value = value * -1 if self.invert else value

        return value

    def input_value(self, key, value):
        return self._input_value_coefficient(key, value)

    def __getattr__(self, key):
        try:
            vtype, fallback = self._frontend_keys[key]
        except KeyError:
            raise AttributeError('{} does not exist as a valid frontend key'.format(key))

        try:
            if vtype == bool:
                return True if self.frontend_config[self.frontend_section][key] \
                    in ('True', 'true', 'y', '1') else False
            else:
                return vtype(self.frontend_config[self.frontend_section][key])
        except KeyError:
            if fallback is not _UNSET:
                return fallback
            else:
                return _UNSET

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)
