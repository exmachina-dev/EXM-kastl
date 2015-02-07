# -*- coding: utf-8 -*-

import configparser
import liblo as lo

import ertza.errors as err

class OSCBaseServer(lo.ServerThread):
    """
    Main OSC class herited from liblo.ServerThread

    Provides basic method to init and configure an OSC server working in a
    RemoteWorker instance.

    Require a ConfigParser object (or a proxy) as init argument.
    """

    def __init__(self, config, logger, restart_event):
        """
        Init OSCServer with a ConfigParser() instance and get server and client
        port.
        """

        self.config = config
        self.lg = logger
        self.osc_event = restart_event

        self.server_port = int(self.config.get('osc', 'server_port', 7900))
        self.client_port = int(self.config.get('osc', 'client_port', 7901))
        super(OSCBaseServer, self).__init__(self.server_port, lo.UDP)

        self.ready = True

    def start(self):
        """
        Start the OSC Server thread.
        """

        super(OSCBaseServer, self).start()
        self.lg.debug("OSCServer started on %s", self.server_port)

    def restart(self):
        """
        Restart the OSC Server thread.

        Actually set the restart event. Restarting is handle by the
        RemoteWorker.
        """

        self.osc_event.set()

    def send(self, dst, msg):
        super(OSCBaseServer, self).send(lo.Address(dst.get_hostname(), self.client_port), msg)

class OSCServer(OSCBaseServer):
    """
    OSCCommands contains all commands available thru OSCServer.
    """
    _commands_store = {

    }

    def setup_reply(self, sender, *args):
        _msg = lo.Message('/setup/return', *args)
        self.send(sender, _msg)

    @lo.make_method('/setup/set', 'ssi')
    @lo.make_method('/setup/set', 'ssh')
    @lo.make_method('/setup/set', 'ssf')
    @lo.make_method('/setup/set', 'ssd')
    @lo.make_method('/setup/set', 'ssc')
    @lo.make_method('/setup/set', 'sss')
    @lo.make_method('/setup/set', 'ssS')
    @lo.make_method('/setup/set', 'ssm')
    @lo.make_method('/setup/set', 'ssT')
    @lo.make_method('/setup/set', 'ssF')
    @lo.make_method('/setup/set', 'ssN')
    @lo.make_method('/setup/set', 'ssI')
    @lo.make_method('/setup/set', 'ssb')
    def setup_set_callback(self, path, args, types, sender):
        setup_sec, setup_opt, args, = args

        try:
            self.config.set(setup_sec, setup_opt, str(args))
            self.setup_reply(sender, setup_sec, setup_opt, True)
        except configparser.NoOptionError as e:
            self.setup_reply(sender, setup_sec, str(e))
        except configparser.NoSectionError as e:
            self.setup_reply(sender, str(e))
        except:
            self.setup_reply(sender, str(ValueError))

        self.lg.debug('Executed %s %s.%s %s (%s) from %s',
                path, setup_sec, setup_opt, args, types, sender.get_hostname())
        return 0

    @lo.make_method('/setup/get', 'ss')
    @lo.make_method('/setup/get', 's')
    @lo.make_method('/setup/get', '')
    def setup_get_callback(self, path, args, types, sender):
        if len(args) != 2:
            self.setup_reply(sender, "One or more argument is missing.")
            return 1
        setup_section, setup_var = args
        try:
            args.append(self.config.get(setup_section, setup_var))
            self.setup_reply(sender, *args)
        except configparser.NoOptionError as e:
            self.setup_reply(sender, setup_section, str(repr(e)))
        return 0

    @lo.make_method('/setup/save', '')
    def setup_save_callback(self, path, args, types, sender):
        self.config.save()

        return 0

    @lo.make_method('/osc/restart', '')
    def osc_restart_callback(self, path, args, types, sender):
            self.setup_reply(sender, path, "Restarting.")
            self.restart()

    @lo.make_method(None, None)
    def fallback_callback(self, path, args, types, sender):
        self.setup_reply(sender, "Something is wrong…", path, *args)
        return 0

    #def setConfig(self, c):
    #    for k, l in c:
    #        if k in ('feedback',):
    #            if k == 'feedback':
    #                self.feedback = bool(*l)

    #def getConfig(self):
    #    rtn = dict()
    #    rtn.update({'feedback', int(self.feedback), })

    #    return rtn

    #def heartbeat(self, destination, ok=True, src=None):
    #    if ok:
    #        state = '/ok'
    #    else:
    #        state = '/nok'
    #    if not src:
    #        src = 'mother'
    #    self.send(destination, '/heartbeat' + state + '/' + src)
