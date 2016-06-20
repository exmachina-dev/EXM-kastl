#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PySide import QtGui
from PySide import QtCore
import functools

import liblo as lo
import logging as lg

from ertza.processors.osc.message import OscMessage, OscAddress

VERSION = '0.0.1'


class EmbeddedLogHandler(lg.Handler):

    def __init__(self, widget):
        super().__init__()
        self.setLevel(lg.DEBUG)

        self.widget = widget

        self.color = {
            "INFO": QtGui.QColor(0, 0, 0),
            "DEBUG": QtGui.QColor(127, 127, 127),
            "WARNING": QtGui.QColor(127, 127, 0),
            "ERROR": QtGui.QColor(127, 0, 0),
            "CRITICAL": QtGui.QColor(255, 0, 0),
        }
        super().__init__()

    def emit(self, record):
        msg = self.format(record) + '\n'

        self.widget.setTextColor(self.color[record.levelname])

        self.widget.moveCursor(QtGui.QTextCursor.End)
        self.widget.insertPlainText(msg)


console_logger = lg.StreamHandler()
console_formatter = lg.Formatter(
    '%(asctime)s %(name)-36s %(levelname)-8s %(message)s',
    datefmt='%Y%m%d %H:%M:%S')

embedded_formatter = lg.Formatter(
    '%(asctime)s %(name)-20s %(levelname)-7s %(message)s',
    datefmt='%d %H:%M:%S')

logging = lg.getLogger('ertza-gui')
logging.addHandler(console_logger)
console_logger.setFormatter(console_formatter)

logging.setLevel(lg.DEBUG)


class ErtzaOSCServer(lo.ServerThread):
    def __init__(self, to, *args, **kwargs):
        self.to = to
        super(ErtzaOSCServer, self).__init__(*args, **kwargs)

    def reply(self, default_path, sender, *args, **kwargs):
        if kwargs and 'merge' in kwargs.keys():
            kwargs['merge'] = True
        else:
            kwargs['merge'] = False

        try:
            if type(args[0]) == str and args[0][0] == '/':
                args = list(args)
                _msg = lo.Message(args.pop(0), *args)
            elif len(args) >= 2 and kwargs['merge']:
                args = list(args)
                path = args.pop(0)
                _msg = lo.Message(default_path+'/'+path, *args)
            else:
                _msg = lo.Message(default_path, *args)
        except (TypeError, KeyError, IndexError):
            _msg = lo.Message(default_path, *args)
        self.send(sender, _msg)
        return _msg

    @lo.make_method('/alive', None)
    def online_cb(self, path, args, types, sender):
        logging.info('{} is online, listening on {}'.format(*args))
        if self.to.to['dev_addr'] == sender.get_hostname():
            self.reply('/setup/dump', sender)
            self.reply('/motor/status', sender)

    @lo.make_method(None, None)
    def default_cb(self, path, args, types, sender):
        self.to.handle(sender.get_hostname(), path, *args)


class ErtzaActions(object):
    def __init__(self, master):
        self.master = master
        self.connected = False

        self.state = {
            'drive_enable': False,
        }

        self._config = {}

    def load_defaults(self):
        self.master.target_addr.setText('192.168.100.23')
        self.master.target_port.setValue(6969)
        self.master.listen_port.setValue(6969)

        logging.info('Welcome to Ertza debug GUI.')
        logging.info('Version : %s' % (VERSION,))

    def handle(self, sender, path, *args):
        """
        OSC commands loaded: /log/to /config/profile/load /machine/get /config/set /machine/slave/add /config/save /config/profile/save /log/level /slave/ping /slave/register/ok /config/profile/dump /machine/set /slave/set/error /slave/free /machine/slave/remove /slave/get /slave/set /help/list /drive/get /config/get /config/profile/list_options /slave/get/error /slave/register /config/profile/unload /version /machine/slaves /drive/set /slave/set/ok /slave/ping/ok /machine/slave/mode /slave/get/ok /identify /config/profile/set
        """

        if '/error' in path:
            logging.error('Error in response: {} {}'.format(path, ' '.join(args)))
        elif '/ok' in path:
            if self.config_get('debug', False):
                logging.debug('From %s : %s %s' % (sender, path, args))
            if '/machine/get' in path:
                k, v = args
                self.state[k] = v
        else:
            logging.warn('Unexpected response: {} {}'.format(path, ' '.join([str(a) for a in args])))

    def connect(self):
        target_addr = self.config_get('target_addr', '127.0.0.1')
        target_port = self.config_get('target_port', 6969)
        listen_port = self.config_get('listen_port', 6970)

        if self.connected:
            del self.osc_server

        logging.info('Starting server on {}'.format(listen_port))
        self.osc_server = ErtzaOSCServer(self, listen_port, lo.UDP)
        self.osc_server.start()
        logging.info('Setting target to {}:{}'.format(target_addr, target_port))
        self.target = lo.Address(target_addr, target_port)
        self.connected = True

        self.request_state()

    def close(self):
        self.stop()
        root.destroy()

    def send(self, path, *args):
        try:
            if self.connected:
                return self.osc_server.reply(None, self.target, path, *args)
        except OSError as e:
            logging.error(repr(e))

    def drive_toggle(self):
        if self.state['drive_enable']:
            self.master.ctl_drive_enable.set('Drive enable')
        else:
            self.master.ctl_drive_enable.set('Drive disable')

        self.state['drive_enable'] = not self.state['drive_enable']
        self.send('/debug/drive/drive_enable', int(self.state['drive_enable']))

    def request_state(self):
        self.send('/machine/get', 'machine:status')

    def drive_cancel(self):
        self.send('/debug/drive/drive_cancel', 1)

    def drive_clear(self):
        self.send('/debug/drive/clear_errors', 1)

    def stop(self):
        self.speed(0)

    def speed(self, speed=None):
        if speed is not None:
            self.master.ctl_speed.set(speed)
        else:
            speed = self.master.ctl_speed.get()

        self.send('/debug/drive/speed', int(speed))

    def reverse_speed(self):
        speed = self.master.ctl_speed.get()
        self.speed(int(speed * -1))

    def update_status(self):
        self.send('/motor/status')

    def update_field(self, sec, opt, val):
        try:
            self.fields[sec][opt].set(val)
            logging.error('Setting %s.%s to %s' % (sec, opt, val))
        except KeyError:
            logging.error('Unexcepted config %s.%s %s' % (sec, opt, val))
            pass

    def update_device(self, *args):
        pass

    def __setattr__(self, attr, value):
        try:
            super().__setattr__(attr, value)
        except AttributeError:
            if 'set_' == attr[0:4]:
                self._config[attr[4:]] = value
            elif 'isend_' == attr[0:6]:
                self._instant_sender(attr[6:], value)
            else:
                raise AttributeError

    def __getattribute__(self, attr):
        try:
            return super().__getattribute__(attr)
        except AttributeError:
            if 'set_' == attr[0:4]:
                return functools.partial(self._setter, attr[4:])
            elif 'isend_' == attr[0:6]:
                return functools.partial(self._instant_sender, attr[6:])
            elif 'iconf_' == attr[0:6]:
                return functools.partial(self._instant_config, attr[6:])
            elif 'get_' == attr[0:4]:
                return functools.partial(self._getter, attr[4:])
            else:
                raise AttributeError

    def _setter(self, key, value):
        self._config[key] = value

    def _getter(self, key):
        return self._config[key]

    def _instant_sender(self, key, value=1):
        if key.startswith('command_'):
            self.send('/machine/set', 'machine:command:{}'.format(key[8:]), value)
        else:
            self.send('/machine/set', 'machine:{}'.format(key), value)

    def _instant_config(self, key, value=None):
        if key.startswith('profile_'):
            if value is not None:
                self.send('/config/profile/{}'.format(key[8:]), value)
            else:
                self.send('/config/profile/{}'.format(key[8:]))
        else:
            self.send('/machine/set', 'machine:{}'.format(key), value)

    def config_get(self, key, fallback=None):
        try:
            return getattr(self, 'get_{}'.format(key))()
        except KeyError:
            if fallback:
                return fallback
            raise


class ErtzaGui(QtGui.QMainWindow):
    def __init__(self):
        super().__init__()
        self.actions = ErtzaActions(self)

        self.create_widgets()

        self.embedded_log_handler = EmbeddedLogHandler(self.log_list)
        self.embedded_log_handler.setFormatter(embedded_formatter)
        logging.addHandler(self.embedded_log_handler)
        self.embedded_log_handler.setLevel(lg.DEBUG)
        logging.setLevel(lg.DEBUG)

        self.actions.load_defaults()

    def create_widgets(self):
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Plastique'))

        self.statusBar().showMessage('Starting…')

        self.setGeometry(500, 900, 250, 150)
        self.setWindowTitle('Ertza debug GUI')

        main_frame = QtGui.QFrame(self)
        self._main_layout = QtGui.QGridLayout(main_frame)
        self.setCentralWidget(main_frame)

        self._menubar()

        self.show()

        self._device_section()

        self._log_section()

        self._control_section()

        self._config_section()

        self.statusBar().showMessage('Ready.')

    def _menubar(self):
        exit_action = QtGui.QAction(QtGui.QIcon('quit24.png'), '&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)

    def _log_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Log')
        frame.setLayout(grid)

        self.log_list = QtGui.QTextEdit()
        cmd_line = QtGui.QLineEdit()

        grid.addWidget(self.log_list, 0, 0, 9, 0)
        grid.addWidget(cmd_line, 9, 0)

        self.centralWidget().layout().addWidget(frame, 0, 1)

    def _control_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Control')
        frame.setLayout(grid)

        ctl_grid = QtGui.QGridLayout()
        ctl_grid.setSpacing(5)
        ctl_grid.setColumnStretch(0, 1)
        ctl_grid.setColumnStretch(1, 1)
        ctl_grid.setColumnStretch(2, 1)
        ctl_grid.setColumnStretch(3, 1)
        ctl_frame = QtGui.QFrame()
        ctl_frame.setLayout(ctl_grid)

        self.ctl_enable_but = QtGui.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ctl_enable_but.setRange(0, 1)
        self.ctl_cancel_but = QtGui.QPushButton('Drive cancel')
        self.ctl_clear_errors_but = QtGui.QPushButton('Clear errors')
        self.ctl_stop_but = QtGui.QPushButton('Stop')

        self.ctl_enable_but.valueChanged.connect(self.actions.isend_command_enable)
        self.ctl_cancel_but.clicked.connect(self.actions.isend_command_cancel)
        self.ctl_clear_errors_but.clicked.connect(self.actions.isend_command_clear_errors)
        self.ctl_stop_but.clicked.connect(self.actions.isend_command_stop)

        ctl_grid.addWidget(QtGui.QLabel('Drive enable'), 0, 0)
        ctl_grid.addWidget(self.ctl_enable_but, 1, 0)
        ctl_grid.addWidget(self.ctl_cancel_but, 1, 1)
        ctl_grid.addWidget(self.ctl_clear_errors_but, 1, 2)
        ctl_grid.addWidget(self.ctl_stop_but, 1, 3)

        ctl_tabs = QtGui.QTabWidget()

        tq_grid = QtGui.QGridLayout()
        tq_grid.setSpacing(10)

        tq_frame = QtGui.QFrame()
        tq_frame.setLayout(tq_grid)

        self.ctl_torque_ref_input = QtGui.QSpinBox()
        self.ctl_tq_rise_time_input = QtGui.QSpinBox()
        self.ctl_tq_fall_time_input = QtGui.QSpinBox()

        self.ctl_torque_ref_input.valueChanged.connect(self.actions.isend_torque_ref)
        self.ctl_tq_rise_time_input.valueChanged.connect(self.actions.isend_torque_rise_time)
        self.ctl_tq_fall_time_input.valueChanged.connect(self.actions.isend_torque_fall_time)

        self.ctl_torque_ref_input.setRange(-100, 100)
        self.ctl_tq_rise_time_input.setRange(0, 100000)
        self.ctl_tq_fall_time_input.setRange(0, 100000)

        self.ctl_torque_ref_input.setSuffix(' %')
        self.ctl_tq_rise_time_input.setSuffix(' ms')
        self.ctl_tq_fall_time_input.setSuffix(' ms')

        tq_grid.addWidget(QtGui.QLabel('Torque ref'), 0, 0)
        tq_grid.addWidget(self.ctl_torque_ref_input, 0, 1)

        tq_grid.addWidget(QtGui.QLabel('Torque rise time'), 1, 0)
        tq_grid.addWidget(self.ctl_tq_rise_time_input, 1, 1)

        tq_grid.addWidget(QtGui.QLabel('Torque fall time'), 2, 0)
        tq_grid.addWidget(self.ctl_tq_fall_time_input, 2, 1)

        vl_grid = QtGui.QGridLayout()
        vl_grid.setSpacing(10)

        vl_frame = QtGui.QFrame()
        vl_frame.setLayout(vl_grid)

        self.ctl_velocity_ref_input = QtGui.QSpinBox()
        self.ctl_vl_acceleration_input = QtGui.QSpinBox()
        self.ctl_vl_deceleration_input = QtGui.QSpinBox()

        self.ctl_velocity_ref_input.setRange(-100000, 100000)
        self.ctl_vl_acceleration_input.setRange(0, 10000)
        self.ctl_vl_deceleration_input.setRange(0, 10000)

        self.ctl_velocity_ref_input.valueChanged.connect(self.actions.isend_velocity_ref)
        self.ctl_vl_acceleration_input.valueChanged.connect(self.actions.isend_acceleration)
        self.ctl_vl_deceleration_input.valueChanged.connect(self.actions.isend_deceleration)

        self.ctl_velocity_ref_input.setSuffix(' rpm')
        self.ctl_vl_acceleration_input.setSuffix(' ms.s-1')
        self.ctl_vl_deceleration_input.setSuffix(' ms.s-1')

        vl_grid.addWidget(QtGui.QLabel('Velocity ref'), 0, 0)
        vl_grid.addWidget(self.ctl_velocity_ref_input, 0, 1)

        vl_grid.addWidget(QtGui.QLabel('Acceleration'), 1, 0)
        vl_grid.addWidget(self.ctl_vl_acceleration_input, 1, 1)

        vl_grid.addWidget(QtGui.QLabel('Deceleration'), 2, 0)
        vl_grid.addWidget(self.ctl_vl_deceleration_input, 2, 1)

        ps_grid = QtGui.QGridLayout()
        ps_grid.setSpacing(10)

        ps_frame = QtGui.QFrame()
        ps_frame.setLayout(ps_grid)

        self.ctl_position_ref_input = QtGui.QSpinBox()
        self.ctl_ps_velocity_input = QtGui.QSpinBox()
        self.ctl_ps_acceleration_input = QtGui.QSpinBox()
        self.ctl_ps_deceleration_input = QtGui.QSpinBox()
        self.ctl_ps_position_mode_input = QtGui.QSpinBox()

        self.ctl_position_ref_input.setRange(-100000000, 100000000)
        self.ctl_velocity_ref_input.setRange(-100000, 100000)
        self.ctl_vl_acceleration_input.setRange(0, 10000)
        self.ctl_vl_deceleration_input.setRange(0, 10000)

        self.ctl_position_ref_input.valueChanged.connect(self.actions.isend_position_ref)
        self.ctl_ps_velocity_input.valueChanged.connect(self.actions.isend_velocity_ref)
        self.ctl_ps_acceleration_input.valueChanged.connect(self.actions.isend_acceleration)
        self.ctl_ps_deceleration_input.valueChanged.connect(self.actions.isend_deceleration)

        self.ctl_position_ref_input.setSuffix(' ticks')
        self.ctl_ps_velocity_input.setSuffix(' rpm')
        self.ctl_ps_acceleration_input.setSuffix(' ms.s-1')
        self.ctl_ps_deceleration_input.setSuffix(' ms.s-1')

        ps_grid.addWidget(QtGui.QLabel('Velocity'), 0, 0)
        ps_grid.addWidget(self.ctl_ps_velocity_input, 0, 1)

        ps_grid.addWidget(QtGui.QLabel('Position ref'), 1, 0)
        ps_grid.addWidget(self.ctl_position_ref_input, 1, 1)

        ps_grid.addWidget(QtGui.QLabel('Acceleration'), 0, 2)
        ps_grid.addWidget(self.ctl_ps_acceleration_input, 0, 3)

        ps_grid.addWidget(QtGui.QLabel('Deceleration'), 1, 2)
        ps_grid.addWidget(self.ctl_ps_deceleration_input, 1, 3)

        ctl_tabs.addTab(tq_frame, '&Torque mode')
        ctl_tabs.addTab(vl_frame, '&Velocity mode')
        ctl_tabs.addTab(ps_frame, '&Position mode')

        grid.addWidget(ctl_frame, 0, 0)
        grid.addWidget(ctl_tabs, 1, 0)

        self.centralWidget().layout().addWidget(frame, 1, 0, 1, 2)

    def _device_section(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(5)

        frame = QtGui.QGroupBox('Connection')
        frame.setLayout(grid)

        self.target_addr = QtGui.QLineEdit()
        self.target_port = QtGui.QSpinBox()
        self.listen_port = QtGui.QSpinBox()
        connect_button = QtGui.QPushButton('Connect')
        debug_checkbox = QtGui.QCheckBox('Debug')

        self.target_port.setRange(0, 99999)
        self.listen_port.setRange(0, 99999)

        self.target_addr.textEdited.connect(self.actions.set_target_addr)
        self.target_port.valueChanged.connect(self.actions.set_target_port)
        self.listen_port.valueChanged.connect(self.actions.set_listen_port)

        debug_checkbox.stateChanged.connect(self.actions.set_debug)
        connect_button.clicked.connect(self.actions.connect)

        grid.addWidget(QtGui.QLabel('IP Address'), 0, 0)
        grid.addWidget(self.target_addr, 0, 1, 1, 3,)

        grid.addWidget(QtGui.QLabel(':'), 0, 4)
        grid.addWidget(self.target_port, 0, 5)

        grid.addWidget(QtGui.QLabel('Listen Port'), 1, 0)
        grid.addWidget(self.listen_port, 1, 1)

        grid.addWidget(debug_checkbox, 1, 5)

        grid.addWidget(connect_button, 2, 1, 1, 4)

        self.centralWidget().layout().addWidget(frame, 0, 0)

    def _config_section(self):
        pass

    def _profile_section(self):
        pass


if __name__ == '__main__':
    root = QtGui.QApplication(sys.argv)
    ertzagui = ErtzaGui()
    sys.exit(root.exec_())
