"""
Oscilloscopes
================

Classes to represent, control, and read out VISA Oscilloscopes.
"""

import visa, numpy as np
import queue, logging, datetime

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
		self.logger = logging.getLogger("oscilloscopes.GenericOscilloscope")
		self.waveformQueue = queue.Queue()

		self.make = "Generic"
		self.model = "Generic Oscilloscope"
		self.serialNumber = '0'
		self.commands = {}

	def __str__(self):
		"""
		Object to String.

		:Returns: A string containing the make, model and serial number of the scope.
		"""
		return "{:s} {:s} Oscilloscope. Serial Number: {:s}.".format(self.make,self.model,self.serialNumber)

	def write(self, toWrite):
		"""
		Writes argument to scope.

		Parameters:
			:toWrite: command to be issued to scope.
		"""
		self.scope.write(toWrite)

	def read(self):
		"""
		Reads one line of scope output.

		:Returns: string of scope output
		"""
		try:
			return self.scope.read().strip()
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
			self.scope.write(command)
			return self.scope.read().strip()
		except Exception as e:
			self.logger.error(e)
			return False

	def setParam(self, command):
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

	def getParam(self, command):
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

	def execCommand(self, command, args=[]):
		"""
		Searches the command dictionary for a command key, and executes the command if it is supported.

		Parameters:
			:command: a key to the command dictionary, usually the name of a function in string form.
			:args: an array of arguments for the desired command

		:returns: a parameter value if requested, True if a parameter is set successfully, or False if communication fails.
		"""

		try:
			if self.commands[command][-1] == '?':
				return self.getParam(self.commands[command])
			else:
				argString = ''

				if args:
					argString = ' '
					for arg in args:
						argString += str(arg) + ' '

				return self.setParam(self.commands[command] + argString)

		except KeyError:
			self.logger.error("Command '{:s}' not supported".format(command))
			return False
		except Exception as e:
			self.logger.error(e)
			return False

	def autosetUnits(self, axisArray):
		"""
		Set the X units of the pyplot to the correct size based on the values in axisArray.

		Parameters:
			:axisArray: the array of values representing one dimension of the waveform.
		"""
		xMax = np.amax(axisArray)
		if xMax > 1e-9:
			if xMax > 1e-6:
				if xMax > 1e-3:
					if xMax > 1:
						prefix = ''
						return [axisArray,prefix]

					prefix = 'milli'
					axisArray = np.multiply(axisArray,1000)
					return [axisArray,prefix]

				prefix = 'micro'
				axisArray = np.multiply(axisArray,1e6)
				return [axisArray,prefix]

			prefix = 'nano'
			axisArray = np.multiply(axisArray,1e9)
			return [axisArray,prefix]

		prefix = ''
		return [axisArray,prefix]

	"""
	AUTOSET COMMAND
	"""

	def autoSet(self):
		"""
		Executes automatic setup of scope window.
		"""

		return self.execCommand('autoSet')

	"""
	ACQUISITION COMMANDS
	"""

	def getAcquisitionParams(self):
		"""
		:Returns: scope acquisition parameters as a string.
		"""

		return self.execCommand('getAcquisitionParams')

	def setAcquisitionMode(self, mode):
		"""
		Set scope acquisition mode.

		:Parameters:
			:mode: Desired mode of scope operation: {SAMPLE | PEAK | AVERAGE}

		:Returns: True if setting is successful, false otherwise.
		"""

		return self.execCommand('setAcquisitionMode',[str(mode)])

	def getAcquisitionMode(self):
		"""
		:Returns: String naming current acquisition mode.
		"""

		return self.execCommand('getAcquisitionMode')

	def getNumberOfAcquisitions(self):
		"""
		:Returns: the number of acquisitions made.
		"""

		return self.execCommand('getNumberOfAcquisitions')

	def setAcqsForAverage(self, acqs):
		"""
		Set the number of acquisitions made to find an average waveform in AVERAGE mode.

		:Parameters:
			:acqs: desired number of acquisitions per average reading: {4 | 16 | 64 | 128}

		:Returns: True if setting is successful, false otherwise.
		"""

		return self.execCommand('setAcqsForAverage',[str(acqs)])

	def getAcqsForAverage(self):
		"""
		:Returns: the current number of acquisitions taken to find an average waveform in AVERAGE mode.
		"""

		return self.execCommand('getAcqsForAverage')

	def setAcqState(self, state):
		"""
		Sets the scope's acquisition state.

		:Parameters:
			:state: a string naming the desired acquisition state: { OFF | ON | RUN | STOP | <NR1> }

		:Returns: True if setting is successful, false otherwise.
		"""

		return self.execCommand('setAcqState',[str(state)])

	def getAcqState(self):
		"""
		:Returns: '0' for off, '1' for on.
		"""

		return self.execCommand('getAcqState')

	def setAcqStop(self, stop):
		"""
		Tells the oscilloscope when to stop taking acquisitions.

		:Returns: True if setting is successful, False otherwise.
		"""

		return self.execCommand('setAcqStop',[str(stop)])

	def getAcqStop(self):
		"""
		:Returns: string describing when the scope stops taking acquisitions, or False if this fails.
		"""

		return self.execCommand('getAcqStop')

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

		return self.execCommand('calibrate')

	def abortCalibrate(self):
		"""
		Stops an in-progress factory calibration process.

		:Returns: True if setting is successful, False otherwise.
		"""

		return self.execCommand('abortCalibrate')

	def continueCalibrate(self):
		"""
		Perform the next step in the factory calibration sequence.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.execCommand('continueCalibrate')

	def factoryCalibrate(self):
		"""
		Initialize factory calibration sequence.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.execCommand('factoryCalibrate')

	def internalCalibrate(self):
		"""
		Initialize internal calibration sequence.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.execCommand('internalCalibrate')

	def getCalStatus(self):
		"""
		Return PASS or FAIL status of the last self or factory-calibration operation.

		:Returns: "PASS" if last calibration was successful, "FAIL" otherwise.
		"""

		return self.execCommand('getCalStatus')

	def getDiagnosticResult(self):
		"""
		Return diagnostic tests status.

		:Returns: "PASS" if scope passes all diagnostic tests, "FAIL" otherwise.
		"""

		return self.execCommand('getDiagnosticResult')

	def getDiagnosticLog(self):
		"""
		Return diagnostic test sequence results.

		:Returns: A comma-separated string containing the results of internal diagnostic routines.
		"""

		return self.execCommand('getDiagnosticLog').strip()

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

		return self.execCommand('getCursor')

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

		return self.execCommand('getAllEvents')

	def isBusy(self):
		"""
		Check if the scope is busy.

		:Returns: 0 for not busy, 1 for busy.
		"""

		return int(self.execCommand('isBusy'))

	def clearStatus(self):
		"""
		Clears scope event queue and status registers.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.execCommand('clearStatus')

	def eventStatus(self):
		"""
		Check event status register.

		:Returns: the integer value held in the ESR.
		"""

		status = self.execCommand('eventStatus')
		if status:
			return int(status)
		else:
			return None

	def eventCode(self):
		"""
		Get code of last event.

		:Returns: integer error code.
		"""

		return self.execCommand('eventCode')

	def eventMessage(self):
		"""
		Get message associated with last scope event.

		:Returns: event code and event message string, separated by a comma.
		"""

		return self.execCommand('eventMessage')

	def getFirstError(self):
		"""
		Returns first message in error log.

		:Returns: a string describing an internal scope error, empty string if error queue is empty.
		"""

		return self.execCommand('getFirstError')

	def getNextError(self):
		"""
		Returns next message in error log.

		:Returns: a string describing an internal scope error, empty string if error queue is empty.
		"""

		return self.getParam('getNextError')

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

		return self.execCommand('getTriggerStatus')

	def getTrigFrequency(self):
		"""
		Read the trigger frequency.
		"""

		return self.execCommand('getTrigFrequency')

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

		return self.execCommand('getDataChannel')

	def setDataChannel(self, channel):
		"""
		Sets the scope's active data channel for USB readout.

		Parameters:
			:channel: the desired data channel.
		"""

		return execCommand('setDataChannel',[str(channel)])

	"""
	END DATA COMMANDS
	"""

class TDS2024B(GenericOscilloscope):
	"""
	Class representing Tektronix 2024B.

	Contains the command dictionary specifying the correct VISA commands for this oscilloscope,
	And defines how to handle waveforms that this scope generates.
	"""

	
						
	def __init__(self, VISA, make, model, serialNum, firmware):
		"""
		Constructor.

		Parameters:
			:VISA: object representing VISA instrument, on which PyVisa can be used.
			:brand: brand of scope
			:model: model of scope
			:serial: serial number of scope
			:firmware: scope firmware version
		"""

		GenericOscilloscope.__init__(self,VISA)
		self.logger = logging.getLogger("oscilloscopes.TDS2024B")

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
					}

		self.make = make
		self.model = model
		self.serialNumber = serialNum
		self.firmwareVersion = firmware
		self.waveformSet = False
		self.numChannels = 4 # 4-channel oscilloscope
		if(self.eventStatus()):
			self.logger.info(self.getAllEvents())

	"""
	WAVEFORM COMMANDS
	"""
		
	def waveformSetup(self):
		"""
		Acquires and stores all necessary parameters for waveform transfer and display.
		"""
		self.waveform = {'Error' : None}

		self.waveform['Data Channel'] = self.getDataChannel() 	# get active channel
		try:
			preamble = self.query("WFMP?").split(';')	# get waveform preamble and parse it
			self.waveform['Data Width']= int(preamble[0])
			self.waveform['Bits Per Point'] = int(preamble[1])
			self.waveform['Encoding'] = preamble[2]
			self.waveform['Binary Format'] = preamble[3]
			self.waveform['Significant Bit'] = preamble[4]
			if len(preamble) > 5: # normal operation
				self.waveform['Number of Points'] = int(preamble[5])
				self.waveform['Point Format'] = preamble[7].strip('"')
				self.waveform['X Increment'] = float(preamble[8])
				self.waveform['X Offset'] = float(preamble[9])
				self.waveform['X Zero'] = float(preamble[10])
				self.waveform['X Unit'] = preamble[11].strip('"')
				if self.waveform['X Unit'] == 's':
					self.waveform['X Unit'] = 'Seconds'
				self.waveform['Y Multiplier'] = float(preamble[12])
				self.waveform['Y Zero'] = float(preamble[13])
				self.waveform['Y Offset'] = float(preamble[14])
				self.waveform['Y Unit'] = preamble[15].strip('"')
				self.waveformSet = True
			else: # Selected channel is not active
				self.waveform['Error'] = self.waveform['Data Channel'] + ' is not active. Please select an active channel.'
				self.waveformSet = False
		except Exception as e:
			self.logger.error(e)

	def getCurve(self):
		"""
		Set up waveform acquisition and get curve data.

		:Returns: a list of voltage values describing a captured waveform.
		"""

		if self.waveformSet:
			try:
				curveData = self.query("CURV?").split(',')
				curveData = list(map(int,curveData))
				for i in range(0,len(curveData)):
					curveData[i] = self.waveform['Y Zero'] +self.waveform['Y Multiplier']*(curveData[i]-self.waveform['Y Offset'])
				return curveData

			except AttributeError as e:
				self.logger.error(e)

	def getXArray(self):
		"""
		Get array of x values that matches the y values in the waveform, scaled properly.

		:Returns: the x array needed to plot a waveform.
		"""
		if not self.waveformSet: self.waveformSetup()
		return np.arange(0,self.waveform['Number of Points']*self.waveform['X Increment'],self.waveform['X Increment'])

	def makeWaveform(self):
		"""
		Assemble waveform dictionary and enqueue it for readout.
		"""
		self.waveformSetup()

		if self.waveformSet:
			try:
				self.waveform['Acquisition Time'] = str(datetime.datetime.now())
				curveData = self.getCurve()
				# curveData = list(map(int,curveData))
				# for i in range(0,len(curveData)):
				# 	curveData[i] = self.waveform['Y Zero'] +self.waveform['Y Multiplier']*(curveData[i]-self.waveform['Y Offset'])
				self.waveform['yData'] = curveData
				self.waveform['xData'] = np.arange(0,self.waveform['Number of Points']*self.waveform['X Increment'],self.waveform['X Increment'])
				self.waveformQueue.put(self.waveform)
				self.logger.info("Waveform made successfully")

			except Exception as e:
				self.logger.error(e)
		else:
			self.waveformQueue.put(self.waveform)

	def getNextWaveform(self):
		"""
		:Returns: The next waveform object in the queue, or None if it is empty
		"""

		if self.waveformQueue.qsize():
			return self.waveformQueue.get()
		else:
			return None

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
			if int(channel) in range(1,self.numChannels+1):
				ch_string = "CH" + channel
				return self.setParam("DAT:SOU " + ch_string)
			else:
				self.logger.error('Invalid data channel: %d', int(channel))
				return False
		except:
			if channel.lower() == 'math':
				ch_string = "MATH"
				return self.setParam("DAT:SOU " + ch_string)
			else:
				self.logger.error('Invalid data channel: %s', channel)
				return False

	"""
	END DATA CHANNEL COMMANDS
	"""













