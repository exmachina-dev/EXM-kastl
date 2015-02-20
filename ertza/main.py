# -*- coding: utf-8 -*-

import multiprocessing as mp
import signal

from ertza.config import ConfigParser
from ertza.config import ConfigWorker

from ertza.utils import LogWorker

from ertza.remotes import RemoteWorker
from ertza.remotes import OSCWorker
from ertza.remotes import ModbusWorker


class MainInitializer(object):
    """
    Main class

    Initialize all master processes such as remote, config and motor.
    Also initialize a LogWorker for debug purposes.
    """

    manager = mp.Manager()
    log_queue = manager.Queue()

    # Some events
    exit_event = manager.Event()
    config_event = manager.Event()
    osc_event = manager.Event()
    modbus_event = manager.Event()
    blockall_event = manager.Event()

    # Some locks
    config_lock = manager.Lock()
    init_lock = manager.Lock()

    # Config pipes
    cnf_log_pipe = mp.Pipe()
    cnf_rmt_pipe = mp.Pipe()
    cnf_osc_pipe = mp.Pipe()
    cnf_mdb_pipe = mp.Pipe()

    def __init__(self):
        self.jobs = []

    def processes(self):
        self.jobs = [
                mp.Process(target=LogWorker, name='ertza.log',
                    args=(self,)),
                mp.Process(target=ConfigWorker, name='ertza.cnf',
                    args=(self,)),
                mp.Process(target=RemoteWorker, name='ertza.rmt',
                    args=(self,)),
                mp.Process(target=OSCWorker, name='ertza.osc',
                    args=(self,)),
                mp.Process(target=ModbusWorker, name='ertza.mdb',
                    args=(self,)),
                ]

    def start(self):
        for j in self.jobs:
            j.start()

    def exit(self):
        self.exit_event.set()

    def join(self):
        for j in self.jobs:
            j.join()
        self.log_queue.put_nowait(None)

if __name__ == "__main__":
    # Save a reference to the original signal handler for SIGINT.
    default_sigint = signal.getsignal(signal.SIGINT)

    # Set signal handling of SIGINT to ignore mode.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    mi = MainInitializer()
    mi.processes()
    mi.start()

    # Since we spawned all the necessary processes already, 
    # restore default signal handling for the parent process. 
    signal.signal(signal.SIGINT, default_sigint)

    try:
        signal.pause()
    except KeyboardInterrupt:
        mi.exit()
        mi.join()
