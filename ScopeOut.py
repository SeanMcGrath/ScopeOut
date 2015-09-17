#!/usr/bin/python

"""
ScopeOut GUI initialization script
"""

import sys
import signal
import logging
import os

from scopeout.client import ThreadedClient
from scopeout.config import ScopeOutConfig as Config


def main():

    print("Initializing ScopeOut...")

    logger = logging.getLogger('ScopeOut')
    logger.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    log_dir = Config.get('Logging', 'log_dir')

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_path = os.path.join(log_dir, Config.get('Logging', 'log_file'))

    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Initializing ScopeOut...")

    app = ThreadedClient(sys.argv)

    logger.info("ScopeOut initialization completed")

    # Enable keyboard shortcuts to kill from command line
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
