# -*- coding: utf-8 -*-

import sys, os
from queue import Empty

from ertza.base import BaseWorker
from ertza.config import ConfigRequest

import logging
import logging.handlers

class LogWorker(BaseWorker):

    def __init__(self, sm):
        super(LogWorker, self).__init__(sm)
        self.config_pipe = self.initializer.conf_log_pipe[1]
        self.config_request = ConfigRequest(self.config_pipe)

        f = '%(asctime)s %(processName)-10s %(levelname)-8s %(message)s'
        hf = logging.Formatter(f)
        root_logger = logging.getLogger()

        self.wait_for_config()

        self.log_path = self.config_request.get('log', 'log_path')
        self.log_file = os.path.join(self.log_path, 'ertza.log')
        h = logging.handlers.RotatingFileHandler(self.log_file, 'a', 300 10)

        logging.basicConfig(format=f)

        h.setFormatter(hf)
        root_logger.addHandler(h)

        self.run()

    def run(self):
        while not self.exit_event.is_set():
            try:
                record = self.lgq.get(timeout=0.1)
                if record is None: # We send this as a sentinel to tell the listener to quit.
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record) # No level or filter logic applied - just do it!
            except Empty:
                pass
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                import traceback
                print('FATAL:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
