"""
Scope Finder
=================

Polls serial ports to find compatible oscilloscopes and returns them
as Oscilloscope objects.

"""

import logging
import re

from visa import ResourceManager, VisaIOError

from scopeout import oscilloscopes


class ScopeFinder:

    def __init__(self):
        """
        Constructor
        """

        self.logger = logging.getLogger('scopeout.utilities.ScopeFinder')
        self.logger.info('ScopeFinder Initialized')

        self.resource_manager = ResourceManager()
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

        return inst.query(command).strip()  # strip newline

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

        try:
            self.resources = self.resource_manager.list_resources()
        except VisaIOError as e:
            self.resources = []

        if self.resources:
            self.logger.info("%d VISA Resource(s) found", len(self.resources))
            self.instruments = []
            for resource in self.resources:
                try:
                    inst = self.resource_manager.open_resource(resource)
                    self.instruments.append(inst)
                    self.logger.info('Resource {} converted to instrument'.format(resource))
                except Exception as e:
                    self.logger.error(e)
                    print(e)
                    del resource

            for ins in self.instruments:
                try:
                    info = self.query(ins, '*IDN?').split(',')  # Parse identification string
                    if info[1] == 'TDS 2024B':  # TDS 2024B oscilloscope
                        info.append(info.pop().split()[1][3:])  # get our identification string into array format
                        scope = oscilloscopes.TDS2024B(ins, info[1], info[2], info[3])
                        self.scopes.append(scope)
                        self.logger.info("Found %s", str(scope))
                    elif re.match('GDS-1.*A', info[1]):
                        scope = oscilloscopes.GDS1000A(ins, info[1], info[2], info[3])
                        self.scopes.append(scope)
                        self.logger.info("Found %s", str(scope))
                    elif re.match('GDS-2.*A', info[1]):
                        scope = oscilloscopes.GDS2000A(ins, info[1], info[2], info[3])
                        self.scopes.append(scope)
                        self.logger.info("Found %s", str(scope))

                    # Support for other scopes to be implemented here!
                except VisaIOError or IndexError:
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
