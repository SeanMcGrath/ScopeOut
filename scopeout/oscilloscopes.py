"""
Oscilloscopes
================

Classes to represent, control, and read out VISA Oscilloscopes.
"""

import visa
import queue
import logging
import datetime

from scopeout.models import Waveform


def fix_negatives(num):
    """
    Some scopes represent negative numbers as being between 128-256,
    this makes shifts those to the correct negative scale.
    :param num: an integer
    :return: the same number, shifted negative as necessary.
    """

    if num > 128:
        return num - 255
    else:
        return num



class GenericOscilloscope:
    """
    Object representation of scope of unknown make.

    All common scope commands are accessible here. These functions wrap text-based VISA commands,
    which are stored in the 'commands' dictionary object which is re-implemented for each
    supported oscilloscope. Calling these functions invokes execCommand(), which searches the dictionary
    for the associated command string and executes it if it is supported.

    """

    def __init__(self, VISA):
        """
        Constructor.

        Parameters:
            :VISA: object representing VISA instrument, on which PyVisa can be used.
        """
        self.scope = VISA
        self.logger = logging.getLogger("ScopeOut.oscilloscopes.GenericOscilloscope")
        self.waveform_queue = queue.Queue()

        self.make = "Generic"
        self.model = "Generic Oscilloscope"
        self.serial_number = '0'
        self.commands = {}

    def __str__(self):
        """
        Object to String.

        :Returns: A string containing the make, model and serial number of the scope.
        """
        return "{:s} {:s} Oscilloscope. Serial Number: {:s}.".format(self.make, self.model, self.serial_number)

    def write(self, command):
        """
        Writes argument to scope.

        Parameters:
            :command: command to be issued to scope.
        """
        self.scope.write(command)

    def read(self):
        """
        Reads one line of scope output.

        :Returns: string of scope output
        """
        try:
            return self.scope.read_raw().strip()
        except visa.VisaIOError:
            self.logger.error("VISA Error: Command timed out.")
        except Exception as e:
            self.logger.error(e)

    def query(self, command):
        """
        Issues query to scope and returns output.

        Parameters:
            :command: command to be written to scope.

        :Returns: the output of the scope given in response to command, False if command fails.
        """

        try:
            result = self.scope.query(command).strip()
            return result
        except Exception as e:
            self.logger.error(e)
            return

    def set_parameter(self, command):
        """
        Set a scope parameter by issuing a command.

        :Parameters:
            :command: Full command to set parameter, in string form.

        :Returns: True if setting is successful, descriptive error message if unsuccessful.
        """

        try:
            self.write(command)
            result = self.query(self.commands['eventStatus'])
            if int(result) == 0:
                return True
            else:
                return False
        except AttributeError as e:
            self.logger.error(e)
            return False

    def get_parameter(self, command):
        """
        get a scope parameter by issuing a command.

        :Parameters:
            :command: Full command to set parameter, in string form.

        :Returns: desired Parameter if communication is successful, False otherwise.
        """

        try:
            return self.query(command).strip("'")
        except Exception as err:
            self.logger.error(err)
            return False

    def exec_command(self, command, *args):
        """
        Searches the command dictionary for a command key, and executes the command if it is supported.

        Parameters:
            :command: a key to the command dictionary, usually the name of a function in string form.
            :args: an array of arguments for the desired command

        :returns: a parameter value if requested, True if a parameter is set successfully, or False if communication fails.
        """

        try:
            if self.commands[command][-1] == '?':
                return self.get_parameter(self.commands[command])
            else:
                arg_string = ''

                if args:
                    arg_string = ' '
                    for arg in args:
                        arg_string += str(arg) + ' '

                return self.set_parameter(self.commands[command] + arg_string)

        except KeyError:
            self.logger.error("Command '{:s}' not supported".format(command))
            return False
        except Exception as e:
            self.logger.error(e)
            return False

    """
    AUTOSET COMMAND
    """

    def autoSet(self):
        """
        Executes automatic setup of scope window.
        """

        return self.exec_command('autoSet')

    """
    ACQUISITION COMMANDS
    """

    def getAcquisitionParams(self):
        """
        :Returns: scope acquisition parameters as a string.
        """

        return self.exec_command('getAcquisitionParams')

    def setAcquisitionMode(self, mode):
        """
        Set scope acquisition mode.

        :Parameters:
            :mode: Desired mode of scope operation: {SAMPLE | PEAK | AVERAGE}

        :Returns: True if setting is successful, false otherwise.
        """

        return self.exec_command('setAcquisitionMode', [str(mode)])

    def getAcquisitionMode(self):
        """
        :Returns: String naming current acquisition mode.
        """

        return self.exec_command('getAcquisitionMode')

    def getNumberOfAcquisitions(self):
        """
        :Returns: the number of acquisitions made.
        """

        return self.exec_command('getNumberOfAcquisitions')

    def setAcqsForAverage(self, acqs):
        """
        Set the number of acquisitions made to find an average waveform in AVERAGE mode.

        :Parameters:
            :acqs: desired number of acquisitions per average reading: {4 | 16 | 64 | 128}

        :Returns: True if setting is successful, false otherwise.
        """

        return self.exec_command('setAcqsForAverage', [str(acqs)])

    def getAcqsForAverage(self):
        """
        :Returns: the current number of acquisitions taken to find an average waveform in AVERAGE mode.
        """

        return self.exec_command('getAcqsForAverage')

    def setAcqState(self, state):
        """
        Sets the scope's acquisition state.

        :Parameters:
            :state: a string naming the desired acquisition state: { OFF | ON | RUN | STOP | <NR1> }

        :Returns: True if setting is successful, false otherwise.
        """

        return self.exec_command('setAcqState', [str(state)])

    def getAcqState(self):
        """
        :Returns: '0' for off, '1' for on.
        """

        return self.exec_command('getAcqState')

    def setAcqStop(self, stop):
        """
        Tells the oscilloscope when to stop taking acquisitions.

        :Returns: True if setting is successful, False otherwise.
        """

        return self.exec_command('setAcqStop', [str(stop)])

    def getAcqStop(self):
        """
        :Returns: string describing when the scope stops taking acquisitions, or False if this fails.
        """

        return self.exec_command('getAcqStop')

    """
    END ACQUISITON COMMANDS
    """

    """
    CALIBRATION COMMANDS
    """

    def calibrate(self):
        """
        Perform an internal self-calibration and return result status.

        :Returns: string describing result of calibration.
        """

        return self.exec_command('calibrate')

    def abortCalibrate(self):
        """
        Stops an in-progress factory calibration process.

        :Returns: True if setting is successful, False otherwise.
        """

        return self.exec_command('abortCalibrate')

    def continueCalibrate(self):
        """
        Perform the next step in the factory calibration sequence.

        :Returns: True if command is successful, False otherwise.
        """

        return self.exec_command('continueCalibrate')

    def factoryCalibrate(self):
        """
        Initialize factory calibration sequence.

        :Returns: True if command is successful, False otherwise.
        """

        return self.exec_command('factoryCalibrate')

    def internalCalibrate(self):
        """
        Initialize internal calibration sequence.

        :Returns: True if command is successful, False otherwise.
        """

        return self.exec_command('internalCalibrate')

    def getCalStatus(self):
        """
        Return PASS or FAIL status of the last self or factory-calibration operation.

        :Returns: "PASS" if last calibration was successful, "FAIL" otherwise.
        """

        return self.exec_command('getCalStatus')

    def getDiagnosticResult(self):
        """
        Return diagnostic tests status.

        :Returns: "PASS" if scope passes all diagnostic tests, "FAIL" otherwise.
        """

        return self.exec_command('getDiagnosticResult')

    def getDiagnosticLog(self):
        """
        Return diagnostic test sequence results.

        :Returns: A comma-separated string containing the results of internal diagnostic routines.
        """

        return self.exec_command('getDiagnosticLog').strip()

    """
    END CALIBRATION COMMANDS
    """

    """
    CURSOR COMMANDS
    """

    def getCursor(self):
        """
        Get cursor settings.

        :Returns: comma-separated string containing cursor settings.
        """

        return self.exec_command('getCursor')

    """
    END CURSOR COMMANDS
    """

    """
    STATUS AND ERROR COMMANDS
    """

    def getAllEvents(self):
        """
        :Returns: all events in the event queue in string format.
        """

        return self.exec_command('getAllEvents')

    def isBusy(self):
        """
        Check if the scope is busy.

        :Returns: 0 for not busy, 1 for busy.
        """

        return int(self.exec_command('isBusy'))

    def clearStatus(self):
        """
        Clears scope event queue and status registers.

        :Returns: True if command is successful, False otherwise.
        """

        return self.exec_command('clearStatus')

    def eventStatus(self):
        """
        Check event status register.

        :Returns: the integer value held in the ESR.
        """

        status = self.exec_command('eventStatus')
        if status:
            return int(status)
        else:
            return None

    def eventCode(self):
        """
        Get code of last event.

        :Returns: integer error code.
        """

        return self.exec_command('eventCode')

    def eventMessage(self):
        """
        Get message associated with last scope event.

        :Returns: event code and event message string, separated by a comma.
        """

        return self.exec_command('eventMessage')

    def getFirstError(self):
        """
        Returns first message in error log.

        :Returns: a string describing an internal scope error, empty string if error queue is empty.
        """

        return self.exec_command('getFirstError')

    def getNextError(self):
        """
        Returns next message in error log.

        :Returns: a string describing an internal scope error, empty string if error queue is empty.
        """

        return self.get_parameter('getNextError')

    """
    END STATUS AND ERROR COMMANDS
    """

    """
    TRIGGER COMMANDS
    """

    def getTriggerStatus(self):
        """
        Read trigger status of TDS2024B.

        :Returns: a string describing trigger status: {AUTO | READY | TRIGGER | ARMED}
        """

        return self.exec_command('getTriggerStatus')

    def getTrigFrequency(self):
        """
        Read the trigger frequency.
        """

        return self.exec_command('getTrigFrequency')

    """
    END TRIGGER COMMANDS
    """

    """
    DATA COMMANDS
    """

    def getDataChannel(self):
        """
        :Returns: The name of the active data channel.
        """

        return self.exec_command('getDataChannel')

    def setDataChannel(self, channel):
        """
        Sets the scope's active data channel for USB readout.

        Parameters:
            :channel: the desired data channel.
        """

        return self.exec_command('setDataChannel', str(channel))

    """
    END DATA COMMANDS
    """

    @property
    def next_waveform(self):
        """
        :Returns: The next waveform object in the queue, or None if it is empty
        """

        if self.waveform_queue.qsize():
            return self.waveform_queue.get()
        else:
            return None


class TDS2024B(GenericOscilloscope):
    """
    Class representing Tektronix 2024B.

    Contains the command dictionary specifying the correct VISA commands for this oscilloscope,
    And defines how to handle waveforms that this scope generates.
    """

    def __init__(self, VISA, model, serial_number, firmware):
        """
        Constructor.

        Parameters:
            :VISA: object representing VISA instrument, on which PyVisa can be used.
            :brand: brand of scope
            :model: model of scope
            :serial: serial number of scope
            :firmware: scope firmware version
        """

        GenericOscilloscope.__init__(self, VISA)
        self.logger = logging.getLogger("ScopeOut.oscilloscopes.TDS2024B")
        self.model = model
        self.serial_number = serial_number
        self.firmwareVersion = firmware
        self.make = 'Tektronix'
        self.numChannels = 4  # 4-channel oscilloscope
        self.commands = {'autoSet': 'AUTOS EXEC',
                         'getAcquisitionParams': 'ACQ?',
                         'setAcquisitionMode': 'ACQ:MOD',
                         'getAcquisitionMode': 'ACQ:MOD?',
                         'getNumberOfAcquisitions': 'ACQ:NUMAC?',
                         'setAcqsForAverage': 'ACQ:NUMAV',
                         'getAcqsForAverage': 'ACQ:NUMAV?',
                         'setAcqState': 'ACQ:STATE',
                         'getAcqState': 'ACQ:STATE?',
                         'setAcqStop': 'ACQ:STOPA',
                         'getAcqStop': 'ACQ:STOPA?',

                         'calibrate': '*CAL?',
                         'abortCalibrate:': 'CAL:ABO',
                         'continueCalibrate': 'CAL:CONTINUE',
                         'factoryCalibrate': 'CAL:FAC',
                         'internalCalibrate': 'CAL:INTERNAL',
                         'getCalStatus': 'CAL:STATUS?',
                         'getDiagnosticResult': 'DIA:RESUL:FLA?',
                         'getDiagnosticLog': 'DIA:RESUL:LOG?',

                         'getCursor': 'CURS?',

                         'getAllEvents': 'ALLE?',
                         'isBusy': 'BUSY?',
                         'clearStatus': '*CLS?',
                         'eventStatus': '*ESR?',
                         'eventCode': 'EVENT?',
                         'eventMessage': 'EVMSG?',
                         'getFirstError': 'ERRLOG:FIRST?',
                         'getNextError': 'ERRLOG:NEXT?',
                         'getTriggerStatus': 'TRIG:STATE?',
                         'getTrigFrequency': 'TRIG:MAIN:FREQ?',

                         'getDataChannel': 'DAT:SOU?',
                         'setDataChannel': 'DAT:SOU'
                         }

        if self.eventStatus:
            self.logger.info(self.getAllEvents())

    """
    WAVEFORM COMMANDS
    """

    def setup_waveform(self):
        """
        Fetch all the parameters needed to parse the wave data.
        will be passed the waveform object.
        :return: the waveform object if setup fails.
        """

        waveform = Waveform()
        waveform.data_channel = self.getDataChannel()  # get active channel
        waveform.capture_time = datetime.datetime.utcnow()

        try:
            preamble = self.query("WFMP?").split(';')  # get waveform preamble and parse it

            if len(preamble) > 5:  # normal operation
                waveform.number_of_points = int(preamble[5])
                waveform.x_increment = float(preamble[8])
                waveform.x_offset = float(preamble[9])
                waveform.x_zero = float(preamble[10])
                waveform.x_unit = preamble[11].strip('"')
                if waveform.x_unit == 's':
                    waveform.x_unit = 'Seconds'
                waveform.y_multiplier = float(preamble[12])
                waveform.y_zero = float(preamble[13])
                waveform.y_offset = float(preamble[14])
                waveform.y_unit = preamble[15].strip('"')

            else:  # Selected channel is not active
                waveform.error = waveform.data_channel \
                                 + ' is not active. Please select an active channel.'

            return waveform

        except Exception as e:
            self.logger.error(e)

    def get_curve(self, wave):
        """
        Set up waveform acquisition and get curve data.

        :Returns: a list of voltage values describing a captured waveform.
        """

        try:
            curveData = self.query("CURV?").split(',')
            curveData = list(map(int, curveData))
            for i in range(0, len(curveData)):
                curveData[i] = wave.y_zero + wave.y_multiplier * (
                    curveData[i] - wave.y_offset)
            return curveData

        except AttributeError as e:
            self.logger.error("Failed to acquire curve data")
        except UnicodeDecodeError as e:
            self.logger.error("Could not decode scope output to ascii")
            raise e

    def make_waveform(self):
        """
        Assemble waveform dictionary and enqueue it for readout.
        """

        wave = self.setup_waveform()
        wave._y_list = self.get_curve(wave)
        self.waveform_queue.put(wave)
        self.logger.info("Waveform made successfully")

    """
    END WAVEFORM COMMANDS
    """

    """
    DATA CHANNEL COMMANDS
    """

    def setDataChannel(self, channel):
        """
        Set data channel of TDS2024B.

        Parameters:
            :channel: a string or int representing the desired data channel

        :Returns: True if a valid channel is passed, False otherwise
        """

        self.logger.info('Received request to set data channel ' + channel)
        try:
            if int(channel) in range(1, self.numChannels + 1):
                ch_string = "CH" + channel
                return self.set_parameter("DAT:SOU " + ch_string)
            else:
                self.logger.error('Invalid data channel: %d', int(channel))
                return False
        except:
            if channel.lower() == 'math':
                ch_string = "MATH"
                return self.set_parameter("DAT:SOU " + ch_string)
            else:
                self.logger.error('Invalid data channel: %s', channel)
                return False

    """
    END DATA CHANNEL COMMANDS
    """


class GDS1000A(GenericOscilloscope):
    """
    Class representing Gwinstek GDS-1000A series oscilloscope.

    Contains the command dictionary specifying the correct VISA commands for this oscilloscope,
    And defines how to handle waveforms that this scope generates.
    """

    def __init__(self, VISA, model, serial_number, firmware):
        """
        Constructor.

        Parameters:
            :VISA: object representing VISA instrument, on which PyVisa can be used.
            :brand: brand of scope
            :model: model of scope
            :serial: serial number of scope
            :firmware: scope firmware version
        """

        GenericOscilloscope.__init__(self, VISA)
        self.logger = logging.getLogger("oscilloscopes.GDS-1000A")
        self.model = model
        self.serial_number = serial_number
        self.firmwareVersion = firmware
        self.make = 'Gwinstek'
        self.numChannels = 2
        self.commands = {'autoSet': 'AUTOS EXEC',
                         'getAcquisitionParams': 'ACQ?',
                         'setAcquisitionMode': 'ACQ:MOD',
                         'getAcquisitionMode': 'ACQ:MOD?',
                         'getNumberOfAcquisitions': 'ACQ:NUMAC?',
                         'setAcqsForAverage': 'ACQ:NUMAV',
                         'getAcqsForAverage': 'ACQ:NUMAV?',
                         'setAcqState': 'ACQ:STATE',
                         'getAcqState': 'ACQ:STATE?',
                         'setAcqStop': 'ACQ:STOPA',
                         'getAcqStop': 'ACQ:STOPA?',

                         'calibrate': '*CAL?',
                         'abortCalibrate:': 'CAL:ABO',
                         'continueCalibrate': 'CAL:CONTINUE',
                         'factoryCalibrate': 'CAL:FAC',
                         'internalCalibrate': 'CAL:INTERNAL',
                         'getCalStatus': 'CAL:STATUS?',
                         'getDiagnosticResult': 'DIA:RESUL:FLA?',
                         'getDiagnosticLog': 'DIA:RESUL:LOG?',

                         'getCursor': 'CURS?',

                         'getAllEvents': 'ALLE?',
                         'isBusy': 'BUSY?',
                         'clearStatus': '*CLS?',
                         'eventStatus': '*ESR?',
                         'eventCode': 'EVENT?',
                         'eventMessage': 'EVMSG?',
                         'getFirstError': 'ERRLOG:FIRST?',
                         'getNextError': 'ERRLOG:NEXT?',
                         'getTriggerStatus': ':TRIG:STATE?',
                         'getTrigFrequency': 'TRIG:MAIN:FREQ?',

                         'getDataChannel': 'DAT:SOU?',
                         }


class GDS2000A(GenericOscilloscope):
    """
    Gwinstek GDS-2000A Series Oscilloscope
    """

    def __init__(self, VISA, model, serial_number, firmware):

        GenericOscilloscope.__init__(self, VISA)
        self.logger = logging.getLogger("oscilloscopes.GDS-2000A")
        self.model = model
        self.serial_number = serial_number
        self.firmwareVersion = firmware
        self.make = 'Gwinstek'
        self.numChannels = 4
        self.commands = {'autoSet': 'AUTOS EXEC',
                         'getAcquisitionParams': 'ACQ?',
                         'setAcquisitionMode': 'ACQ:MOD',
                         'getAcquisitionMode': 'ACQ:MOD?',
                         'getNumberOfAcquisitions': 'ACQ:NUMAC?',
                         'setAcqsForAverage': 'ACQ:NUMAV',
                         'getAcqsForAverage': 'ACQ:NUMAV?',
                         'setAcqState': 'ACQ:STATE',
                         'getAcqState': 'ACQ:STATE?',
                         'setAcqStop': 'ACQ:STOPA',
                         'getAcqStop': 'ACQ:STOPA?',

                         'calibrate': '*CAL?',
                         'abortCalibrate:': 'CAL:ABO',
                         'continueCalibrate': 'CAL:CONTINUE',
                         'factoryCalibrate': 'CAL:FAC',
                         'internalCalibrate': 'CAL:INTERNAL',
                         'getCalStatus': 'CAL:STATUS?',
                         'getDiagnosticResult': 'DIA:RESUL:FLA?',
                         'getDiagnosticLog': 'DIA:RESUL:LOG?',

                         'getCursor': 'CURS?',

                         'getAllEvents': 'ALLE?',
                         'isBusy': 'BUSY?',
                         'clearStatus': '*CLS?',
                         'eventStatus': '*ESR?',
                         'eventCode': 'EVENT?',
                         'eventMessage': 'EVMSG?',
                         'getFirstError': 'ERRLOG:FIRST?',
                         'getNextError': 'ERRLOG:NEXT?',
                         'getTriggerStatus': ':TRIG:STATE?',
                         'getTrigFrequency': 'TRIG:MAIN:FREQ?',

                         'getDataChannel': 'DAT:SOU?',
                         'setDataChannel': 'DAT:SOU'
                         }

    def setup_waveform(self):

        waveform = Waveform()

        preamble = self.query('ACQ1:MEM?').strip().split(';')
        wave_header = {}
        for entry in preamble:
            entry_parts = entry.split(',')
            if len(entry_parts) == 2:
                wave_header[entry_parts[0]] = entry_parts[1]

        waveform.capture_time = waveform.capture_time = datetime.datetime.utcnow()
        waveform.data_channel = wave_header['Source']
        waveform.number_of_points = int(wave_header['Memory Length'])
        waveform.x_unit = wave_header['Horizontal Units']
        if waveform.x_unit.lower() == 's':
            waveform.x_unit = 'Seconds'
        waveform.x_scale = float(wave_header['Horizontal Scale'])
        waveform.y_unit = wave_header['Vertical Units']
        if waveform.y_unit.lower() == 'V':
            waveform.y_unit = 'Volts'
        waveform.y_scale = float(wave_header['Vertical Scale'])

        return waveform

    def make_waveform(self):

        waveform = self.setup_waveform()
        y_multiplier = waveform.y_scale/256
        raw = self.read()[9:]

        try:
            while True:
                raw += self.read()
        except:
            pass

        raw = [y_multiplier * fix_negatives(num) for num in list(raw) if num not in [0, 255]]
        waveform._y_list = raw
        self.waveform_queue.put(waveform)

