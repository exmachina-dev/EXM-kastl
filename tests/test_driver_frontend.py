# -*- coding: utf-8 -*-

import pytest

from kastl.drivers import DriverFrontend


class Test_DriverFrontend(object):
    def setup_class(self):
        self.conf = {
            'motor': {
                'torque_constant': 5,
                'drive_rated_current': 2,

                'gearbox_input_coefficient': 1,
                'gearbox_output_coefficient': 10,

                'max_velocity': 5000,
                'max_acceleration': 5000,
                'max_deceleration': 5000,

                'custom_max_velocity': '500',

                'application_coefficient': 1,
            },
        }

        self.fe = DriverFrontend()
        self.fe.load_config(self.conf)

    def test_config(self):

        assert self.fe.max_velocity == 5000.0
        assert self.fe.custom_max_velocity == 500.0

        assert self.fe.torque_constant == 5
        assert self.fe.drive_rated_current == 2

        assert self.fe.acceleration_time_mode is False

    def test_output(self):
        with pytest.raises(KeyError):
            self.fe['nonexistingkey']

        assert self.fe.output_value('nonexistingkey', 500) == 500

        assert self.fe.output_value('velocity_ref', 400) == 4000   # multiplied by gearbox_ratio

        assert self.fe.output_value('position_ref', 400) == 4000   # multiplied by gearbox_ratio

        assert self.fe.output_value('torque_ref', 10) == 1000.0

    def test_input(self):
        assert self.fe.input_value('nonexistingkey', 500) == 500

        assert self.fe.input_value('velocity_ref', 400) == 40      # multiplied by gearbox_ratio

        assert self.fe.input_value('position_ref', 4000) == 400.0

        assert self.fe.input_value('torque_ref', 100) == 1.0

    def test_coeff(self):
        keys = ('velocity_ref', 'position_ref', 'torque_ref', 'acceleration', 'deceleration')
        ovalues = (100.0, 100.0, 1000.0, 100, 100)
        ivalues = (10.0, 10.0, 1.0, 10, 10)

        for i, k in enumerate(keys):
            assert self.fe.output_value(k, 10) == ovalues[i]
            assert self.fe.input_value(k, 100) == ivalues[i]

        self.conf['motor']['application_coefficient'] = '2'

        for i, k in enumerate(keys):
            assert self.fe.output_value(k, 10) == ovalues[i] * 2
            assert self.fe.input_value(k, 100) == ivalues[i] / 2

        self.conf['motor']['application_coefficient'] = '1.0'

    def test_invert(self):
        keys = ('velocity_ref', 'position_ref', 'torque_ref')
        ovalues = (100.0, 100.0, 1000.0)
        ivalues = (10.0, 10.0, 1.0)

        self.conf['motor']['application_coefficient'] = '1.0'

        for i, k in enumerate(keys):
            assert self.fe.output_value(k, 10) == ovalues[i]
            assert self.fe.input_value(k, 100) == ivalues[i]

        self.conf['motor']['invert'] = 'true'

        for i, k in enumerate(keys):
            assert self.fe.output_value(k, 10) == ovalues[i] * -1
            assert self.fe.input_value(k, 100) == ivalues[i] * -1

        self.conf['motor']['invert'] = 'false'

    def test_limits(self):
        keys = ('velocity_ref', 'position_ref', 'acceleration', 'deceleration')
        values = (5000.0, 50000.0, 8000.0, 8000.0)

        self.conf['motor']['custom_max_position'] = 5000
        self.conf['motor']['custom_min_position'] = -5000
        self.conf['motor']['max_acceleration'] = 8000
        self.conf['motor']['max_deceleration'] = 8000
        self.conf['motor']['custom_max_velocity'] = 500

        for i, k in enumerate(keys):
            assert self.fe.output_value(k, 10000) == values[i]

        keys = ('torque_rise_time', 'torque_fall_time')
        values = (80, 80)

        self.conf['motor']['min_torque_rise_time'] = 80
        self.conf['motor']['min_torque_fall_time'] = 80

        for i, k in enumerate(keys):
            assert self.fe.output_value(k, 10) == values[i]
