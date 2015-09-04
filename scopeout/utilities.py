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


class OscilloscopeCreationError(Exception):
    """
    Raised when an Oscilloscope cannot be instantiated.
    """
    pass


def make_scope(instrument, idn_result):
    """
    Factory for Oscilloscope objects. Takes the result of the *IDN? query and
    instantiates the correct Oscilloscope.
    :param instrument: the VISA instrument for the oscilloscope.
    :param idn_result: the string result of the *IDN? query
    :return: A new Oscilloscope.
    :raises: an OscilloscopeCreationError if scope creation fails.
    """

    try:
        scope_info = tuple(idn_result.split(','))
        assert len(scope_info) >= 4
        scope_model = scope_info[1]

        if re.match('TDS 2.*B', scope_model):
            return oscilloscopes.TDS2000B(instrument, *scope_info[1:])
        elif re.match('GDS-1.*A', scope_model):
            return oscilloscopes.GDS1000A(instrument, *scope_info[1:])
        elif re.match('GDS-2.*A', scope_model):
            return oscilloscopes.GDS2000A(instrument, *scope_info[1:])

    except Exception as e:
        raise OscilloscopeCreationError(e)


class ScopeFinder:

    def __init__(self):

        self.logger = logging.getLogger('scopeout.utilities.ScopeFinder')
        self.logger.info('ScopeFinder Initialized')

        self.resource_manager = ResourceManager()
        self.scopes = []
        self.refresh()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
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

    def refresh(self):
        """
        Re-run scope acquisition to update scope array.

        :Returns: the ScopeFinder object, for convenience.
        """

        self.scopes = []

        try:
            resources = self.resource_manager.list_resources()
        except VisaIOError:
            resources = []

        if resources:
            self.logger.info("%d VISA Resource(s) found", len(resources))
            instruments = []
            for resource in resources:
                try:
                    inst = self.resource_manager.open_resource(resource)
                    instruments.append(inst)
                    self.logger.info('Resource {} converted to instrument'.format(resource))
                except Exception as e:
                    self.logger.error(e)

            for instrument in instruments:
                try:
                    # Get the ID information
                    info = self.query(instrument, '*IDN?')
                    read_attempts = 0
                    while read_attempts < 100 and not len(info.split(',')) == 4:
                        # We didn't get the ID, read until we do
                        info = instrument.read_raw().strip()
                        read_attempts += 1
                        # Stop after 100 attempts, something is wrong
                        if read_attempts is 100:
                            raise OscilloscopeCreationError('Failed to read ID information from ' + str(instrument))

                    self.scopes.append(make_scope(instrument, info))

                except VisaIOError as e:
                    if 'VI_ERROR_CONN_LOST' in str(e):
                        self.resource_manager = ResourceManager()
                    elif 'VI_ERROR_TMO' not in str(e):
                        self.logger.error(e)
                except OscilloscopeCreationError as e:
                    self.logger.error('Oscilloscope connection error: ' + str(e))
                except Exception as e:
                    self.logger.error(e)

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


