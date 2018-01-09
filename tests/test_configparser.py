# -*- coding: utf-8 -*-

import pytest

import os

from kastl.configparser import ConfigParser, NoSectionError, NoOptionError


class Test_ConfigParser(object):
    def setup_class(self):
        self.base_path = os.path.dirname(os.path.realpath(__file__))
        self.cf = ConfigParser('{}/test.conf'.format(self.base_path))

    def test_load_variant(self):
        self.cf.load_variant('variant', variant_path=self.base_path)

    def test_load_profile(self):
        self.cf.load_profile('profile', profile_path=self.base_path)

    def test_get(self):
        assert self.cf['machine']['profile'] == 'profile'

        with pytest.raises(NoSectionError):
            self.cf.get('fake_section', 'fake_option')

        # Broken for now
        # with pytest.raises(NoOptionError):
        #     self.cf.get('machine', 'fake_option')

        assert self.cf.get('fake_section', 'fake_option', fallback=1234) == 1234

        # Broken for now
        # assert self.cf['machine']['force_serialnumber'] == '0000'

    def test_precedence(self):
        """
        Check precedence
        With machine:test = 1 in test.conf
        With machine:test = 2 in variant.conf
        With machine:test = 3 in profile.conf
        """
        assert self.cf.get('machine', 'test_variant', fallback=4) == '2'
        assert self.cf.get('machine', 'test_profile', fallback=4) == '3'

        assert self.cf['machine']['test_variant'] == '2'
        assert self.cf['machine']['test_profile'] == '3'

    def test_set(self):
        with pytest.raises(KeyError):
            self.cf['fake_section']['fake_option'] = 0

        with pytest.raises(TypeError):
            self.cf['machine']['force_serialnumber'] = 0

        self.cf['machine']['force_serialnumber'] = '1111'
        assert self.cf['machine']['force_serialnumber'] == '1111'
