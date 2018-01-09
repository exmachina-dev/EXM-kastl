# -*- coding: utf-8 -*-

from kastl.commands import UnbufferedCommand
from kastl.commands import OscCommand


class ConfigProfileLoad(UnbufferedCommand, OscCommand):
    """
    Load existing profile found in _PROFILE_PATH (usually /etc/kastl/profiles)
    """

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            profile, = c.args
            self.machine.config.load_profile(profile)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/load'

    @property
    def help_text(self):
        return 'Load the specified PROFILE'

    @property
    def args(self):
        return 'PROFILE'


class ConfigProfileUnload(UnbufferedCommand, OscCommand):
    """
    Unload loaded profile (if any)
    """

    def execute(self, c):
        try:
            self.machine.config.unload_profile()
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/unload'

    @property
    def help_text(self):
        return 'Unload the loaded profile (if any)'


class ConfigProfileSet(UnbufferedCommand, OscCommand):
    """
    Set value in profile (not in config)
    """

    def execute(self, c):
        if not self.check_args(c, 'eq', 2):
            return

        try:
            dest, value = c.args
            sec, opt = dest.split(':')
            self.machine.config.profile_set(sec, opt, value)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/set'

    @property
    def help_text(self):
        return 'Set the VALUE in SECTION:OPTION'

    @property
    def args(self):
        return 'SECTION:OPTION VALUE'


class ConfigProfileListOptions(UnbufferedCommand, OscCommand):
    """
    Return a list of assignable options:
    /config/profile/list_options/reply SECTION:OPTION

    The command always send a ok reply at the end of the dump:
    /config/profile/list_options/ok done
    """
    def execute(self, c):

        try:
            list_opts = self.machine.config.get_profile_options()
            for sec, opts in list_opts.items():
                for opt, data in opts.items():
                    if data[1] is not None:
                        self.reply(c, '{s}:{o}'.format(s=sec, o=opt), *data)
                    else:
                        self.reply(c, '{s}:{o}'.format(s=sec, o=opt), data[0])

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/list_options'

    @property
    def help_text(self):
        return 'Return a list of options that can be saved into a profile'


class ConfigProfileClearOption(UnbufferedCommand, OscCommand):
    """
    Clear an assigned option:
    """
    def execute(self, c):

        if not self.check_args(c, 'eq', 1):
            return

        try:
            dest = c.args[0]
            sec, opt = dest.split(':')
            self.machine.config.profile_set(sec, opt, None)
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/clear_option'

    @property
    def help_text(self):
        return 'Clear an assigned option SECTION:OPTION'

    @property
    def args(self):
        return 'SECTION:OPTION'


class ConfigProfileList(UnbufferedCommand, OscCommand):
    """
    Return a list of available profils:
    /config/profile/list/reply PROFILE

    The command always send a ok reply at the end of the dump:
    /config/profile/list/ok done
    """
    def execute(self, c):

        try:
            pfl_list = self.machine.config.get_profiles_list()
            for profile in pfl_list:
                self.reply(c, profile)

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/list'

    @property
    def help_text(self):
        return 'Return a list of available profiles'


class ConfigProfileDump(UnbufferedCommand, OscCommand):
    """
    Dump profile content:
    /config/profile/dump/reply SECTION:OPTION VALUE\r\n

    The command always send a ok reply at the end of the dump:
    /config/profile/dump/ok done\r\n
    """
    def execute(self, c):
        if not self.check_args(c, 'le', 1):
            return

        try:
            if c.args:
                profile, = c.args
            else:
                profile = None

            dump = self.machine.config.dump_profile(profile)
            for options, val in dump.items():
                self.reply(c, profile, '{}:{}'.format(*options), val)

            self.ok(c, 'done')
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/dump'

    @property
    def help_text(self):
        return 'Dump actual profile values '


class ConfigProfileSave(UnbufferedCommand, OscCommand):
    """
    Save profile to a file in _PROFILE_PATH.
    If PROFILE is empty, overwrites the loaded profile
    """

    def execute(self, c):
        if not self.check_args(c, 'le', 1):
            return

        try:
            try:
                profile = c.args[0]
                self.machine.config.save_profile(profile)
            except KeyError:
                self.machine.config.save_profile()

            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/profile/save'

    @property
    def help_text(self):
        return 'Save the specified PROFILE (or the loaded one if unspecified)'

    @property
    def args(self):
        return '[PROFILE]'


class ConfigSave(UnbufferedCommand, OscCommand):
    """
    Save config to custom.conf including the loaded profile name
    """

    def execute(self, c):
        if not self.check_args(c, 'eq', 0):
            return

        try:
            self.machine.config.save()
            self.ok(c)
        except Exception as e:
            self.error(c, str(e))

    @property
    def alias(self):
        return '/config/save'

    @property
    def help_text(self):
        return 'Save the current config into the custom config file'


class ConfigGet(UnbufferedCommand, OscCommand):
    """
    Returns the value of SECTION:OPTION. This allow to verify the behaviour of the config.
    This behaviour can be changed by variant config or profile.
    """

    def execute(self, c):
        if not self.check_args(c, 'eq', 1):
            return

        try:
            k, = c.args
            s, o = k.split(':', maxsplit=1)
            v = self.machine.config[s][o]
            self.ok(c, k, v)
        except KeyError:
            self.error(c, k, 'No such key: {}'.format(k))
        except Exception as e:
            self.error(c, k, str(e))

    @property
    def alias(self):
        return '/config/get'

    @property
    def help_text(self):
        return 'Returns the value of SECTION:OPTION'

    @property
    def args(self):
        return 'SECTION:OPTION'
