"""
Scope Finder
=================

Polls serial ports to find compatible oscilloscopes and returns them
as Oscilloscope objects.

"""

import visa
import logging
import re
import os

from scopeout.config import ScopeOutConfig as Config
from scopeout import oscilloscopes


class ScopeFinder:

    def __init__(self):
        """
        Constructor
        """

        self.logger = logging.getLogger('scopeout.utilities.ScopeFinder')
        self.logger.info('ScopeFinder Initialized')

        self.resources = []
        self.instruments = []
        self.scopes = []

        self.refresh()

    def __enter__(self):
        # Entry point for the *with* statement, which allows this object to close properly on program exit.
        return self

    def __exit__(self, type, value, traceback):
        # Exit point for with statement
        pass

    def query(self, inst, command):
        """
        Issues query to instrument and returns response.

        Parameters:
            :inst: the instrument to be queried.
            :command: the command to be issued.

        :Returns: the response of inst as a string.
        """

        return inst.ask(command).strip()  # strip newline

    def get_scopes(self):
        """
        Getter for array of connected oscilloscopes.

        :Returns: an array of PyVisa instrument objects representing USB oscilloscopes connected to the computer.
        """

        return self.scopes

    def refresh(self):
        """
        Re-run scope acquisition to update scope array.

        :Returns: the ScopeFinder object, for convenience.
        """

        self.scopes = []
        self.resources = []

        rm = visa.ResourceManager()
        try:
            self.resources = rm.list_resources('USB?*')
        except visa.VisaIOError as e:
            self.resources = []

        if self.resources:
            self.logger.info("%d VISA Resource(s) found", len(self.resources))
            self.instruments = []
            for resource in self.resources:
                try:
                    inst = rm.get_instrument(resource)
                    inst.timeout = 10000
                    self.instruments.append(inst)
                    self.logger.info('Resource {} converted to instrument'.format(resource))
                except Exception as e:
                    self.logger.error(e)
                    del resource

            for ins in self.instruments:
                try:
                    info = self.query(ins, '*IDN?').split(',')  # Parse identification string
                    if info[1] == 'TDS 2024B':  # TDS 2024B oscilloscope
                        info.append(info.pop().split()[1][3:])  # get our identification string into array format
                        scope = oscilloscopes.TDS2024B(ins, info[0], info[1], info[2], info[3])
                        self.scopes.append(scope)
                        self.logger.info("Found %s", str(scope))
                    elif re.match('GDS-1.*A', info[1]):
                        scope = oscilloscopes.GDS1000A(ins, info[0], info[1], info[2], info[3])
                        self.scopes.append(scope)
                        self.logger.info("Found %s", str(scope))

                    # Support for other scopes to be implemented here!
                except visa.VisaIOError:
                    self.logger.error('{} could not be converted to an oscilloscope'.format(ins))
        return self

    def check_scope(self, scope_index):
        """
        Check if the scope at scopeIndex is still connected.

        Parameters:
            :scopeIndex: the index of the scopes array to check.

        :Returns: True if connected, false otherwise
        """

        try:
            if self.scopes[scope_index].getTriggerStatus():
                return True
            else:
                return False
        except:
            return False


def get_logger(scope_name):
    """
    Create a new logger that writes to the log file specified in the configuration.
    :param scope_name: The fully qualified name of the scope of the logger, e.g
        scopeout.utilities.get_logger
    :return: a new logger, ready for use
    """

    logger = logging.getLogger(scope_name)

    # create file handler which logs even debug messages
    log_dir = Config.get('Logging', 'log_dir')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, Config.get('Logging', 'log_file')))
    fh.setLevel(logging.INFO)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
