"""
Oscilloscopes
================

Classes to represent, control, and read out VISA Oscilloscopes.
"""

import visa, numpy as np
import queue, logging

class GenericOscilloscope:
	"""
	Object representation of scope of unknown make.
	"""


	def __init__(self, VISA):
		"""
		Constructor.

		Parameters:
			:VISA: object representing VISA instrument, on which PyVisa can be used.
		"""
		self.scope = VISA
		self.logger = logging.getLogger("oscilloscopes.GenericOscilloscope")

		self.make = "Generic"
		self.model = "Generic Oscilloscope"
		self.serialNumber = '0'

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

	def __str__(self):
		"""
		Object to String.

		:Returns: A string containing the make, model and serial number of the scope.
		"""
		return "{:s} {:s} Oscilloscope. Serial Number: {:s}.".format(self.make,self.model,self.serialNumber)

	def setParam(self, command):
		"""
		Set a scope parameter by issuing a command.

		:Parameters:
			:command: Full command to set parameter, in string form.

		:Returns: True if setting is successful, descriptive error message if unsuccessful.
		"""

		try:
			self.write(command)
			result = self.query("*ESR?")
			if result is None:
				return True
			else:
				return self.eventMessage().split(',')[1].strip('"')
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

		try: return self.query(command).strip("'")
		except Exception as err:
			self.logger.error(err)

class TDS2024B(GenericOscilloscope):
	"""
	Class representing Tektronix 2024B.
	"""

	"""
	UTILITY METHODS
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

		self.make = make
		self.model = model
		self.serialNumber = serialNum
		self.firmwareVersion = firmware
		self.waveformSet = False
		self.waveformQueue = queue.Queue()
		self.numChannels = 4 # 4-channel oscilloscope
		if(self.eventStatus()):
			self.logger.info(self.getAllEvents())
		
	def waveformSetup(self):
		"""
		Acquires and stores all necessary parameters for waveform transfer and display.
		"""
		self.waveform = {'error' : None}

		self.query("DAT:SOU?")
		self.waveform['dataChannel'] = self.query("DAT:SOU?") 	# get active channel
		try:
			preamble = self.query("WFMP?").split(';')	# get waveform preamble and parse it
			self.waveform['dataWidth']= int(preamble[0])
			self.waveform['bitsPerPoint'] = int(preamble[1])
			self.waveform['encoding'] = preamble[2]
			self.waveform['binaryFormat'] = preamble[3]
			self.waveform['sigBit'] = preamble[4]
			if len(preamble) > 5: # normal operation
				self.waveform['numberOfPoints'] = int(preamble[5])
				self.waveform['pointFormat'] = preamble[7].strip('"')
				self.waveform['xIncr'] = float(preamble[8])
				self.waveform['xOff'] = float(preamble[9])
				self.waveform['xZero'] = float(preamble[10])
				self.waveform['xUnit'] = preamble[11].strip('"')
				if self.waveform['xUnit'] == 's':
					self.waveform['xUnit'] = 'Seconds'
				self.waveform['yMult'] = float(preamble[12])
				self.waveform['yZero'] = float(preamble[13])
				self.waveform['yOff'] = float(preamble[14])
				self.waveform['yUnit'] = preamble[15].strip('"')
				self.waveformSet = True
			else: # Selected channel is not active
				self.waveform['error'] = self.waveform['dataChannel'] + ' is not active. Please select an active channel.'
				self.waveformSet = False
		except Exception as e:
			self.logger.error(e)

	def getCurve(self):
		"""
		Set up waveform acquisition and get curve data.

		:Returns: a list of voltage values describing a captured waveform.
		"""

		self.waveformSetup()

		if self.waveformSet:
			try:
				curveData = self.query("CURV?").split(',')
				curveData = list(map(int,curveData))
				for i in range(0,len(curveData)):
					curveData[i] = self.waveform['yZero'] +self.waveform['yMult']*(curveData[i]-self.waveform['yOff'])
				return curveData

			except AttributeError as e:
				self.logger.error(e)

	def getXArray(self):
		"""
		Get array of x values, scaled properly
		"""
		if not self.waveformSet: self.waveformSetup()
		return np.arange(0,self.waveform['numberOfPoints']*self.waveform['xIncr'],self.waveform['xIncr'])

	def makeWaveform(self):
		"""
		Assemble waveform dictionary and enqueue it for readout.
		"""
		self.waveformSetup()

		if self.waveformSet:
			try:
				curveData = self.query("CURV?").split(',')
				curveData = list(map(int,curveData))
				for i in range(0,len(curveData)):
					curveData[i] = self.waveform['yZero'] +self.waveform['yMult']*(curveData[i]-self.waveform['yOff'])
				self.waveform['yData'] = curveData
				self.waveform['xData'] = np.arange(0,self.waveform['numberOfPoints']*self.waveform['xIncr'],self.waveform['xIncr'])
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

	def checkTrigger(self):
		"""
		Read trigger status of TDS2024B.

		:Returns: a string describing trigger status: {AUTO | READY | TRIGGER | ARMED}
		"""

		return self.getParam("TRIG:STATE?")

	def getTrigFrequency(self):
		"""
		Read the trigger frequency.
		"""

		return self.getParam("TRIG:MAIN:FREQ?")
		
	def setDataChannel(self, channel):
		"""
		Set data channel of TDS2024B.

		Parameters:
			:channel: a string representing the desired data channel

		:Returns: True if a valid channel is passed, False otherwise
		"""

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
	END UTILITY METHODS
	"""

	"""
	ACQUISITION COMMANDS
	"""

	def getAcquisitionParams(self):
		"""
		:Returns: scope acquisition parameters as a string.
		"""

		return self.getParam("ACQ?")

	def setAcquisitionMode(self, mode):
		"""
		Set TDS2024B acquisition mode.

		:Parameters:
			:mode: Desired mode of scope operation: {SAMPLE | PEAK | AVERAGE}

		:Returns: True if setting is successful, false otherwise.
		"""

		return self.setParam("ACQ:MOD " + str(mode))

	def getAcquisitionMode(self):
		"""
		:Returns: String naming current acquisition mode.
		"""

		return self.getParam("ACQ:MOD?")

	def getNumberOfAcquisitions(self):
		"""
		:Returns: the number of acquisitions made.
		"""

		return self.getParam('ACQ:NUMAC?')

	def setAcqsForAverage(self, acqs):
		"""
		Set the number of acquisitions made to find an average waveform in AVERAGE mode.

		:Parameters:
			:acqs: desired number of acquisitions per average reading: {4 | 16 | 64 | 128}

		:Returns: True if setting is successful, false otherwise.
		"""

		if acqs not in [4,16,64,128]: return False

		return self.setParam("ACQ:NUMAV " +str(acqs))

	def getAcqsForAverage(self):
		"""
		:Returns: the current number of acquisitions taken to find an average waveform in AVERAGE mode.
		"""

		return self.getParam('ACQ:NUMAV?')

	def setAcqState(self, state):
		"""
		Sets the scope's acquisition state.

		:Parameters:
			:state: a string naming the desired acquisition state: { OFF | ON | RUN | STOP | <NR1> }

		:Returns: True if setting is successful, false otherwise.
		"""

		return self.setParam("ACQ:STATE " +str(state))

	def getAcqState(self):
		"""
		:Returns: '0' for off, '1' for on.
		"""

		return self.getParam("ACQ:STATE?")

	def setAcqStop(self, stop):
		"""
		Tells the oscilloscope when to stop taking acquisitions.

		:Returns: True if setting is successful, False otherwise.
		"""

		return self.setParam("ACQ:STOPA " +str(stop))

	def getAcqStop(self):
		"""
		:Returns: string describing when the scope stops taking acquisitions, or False if this fails.
		"""

		return self.getParam("ACQ:STOPA?")

	"""
	END ACQUISITION COMMANDS
	"""

	"""
	CALIBRATION COMMANDS
	"""

	def calibrate(self):
		"""
		Perform an internal self-calibration and return result status.

		:Returns: string describing result of calibration.
		"""

		return self.getParam("*CAL?")

	def abortCalibrate(self):
		"""
		Stops an in-progress factory calibration process.

		:Returns: True if setting is successful, False otherwise.
		"""

		return self.setParam("CAL:ABO")

	def continueCalibrate(self):
		"""
		Perform the next step in the factory calibration sequence.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.setParam("CAL:CONTINUE")

	def factoryCalibrate(self):
		"""
		Initialize factory calibration sequence.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.setParam("CAL:FAC")

	def internalCalibrate(self):
		"""
		Initialize internal calibration sequence.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.setParam("CAL:INTERNAL")

	def getCalStatus(self):
		"""
		Return PASS or FAIL status of the last self or factory-calibration operation.

		:Returns: "PASS" if last calibration was successful, "FAIL" otherwise.
		"""

		return self.getParam("CAL:STATUS?")

	def getDiagnosticResult(self):
		"""
		Return diagnostic tests status.

		:Returns: "PASS" if scope passes all diagnostic tests, "FAIL" otherwise.
		"""

		return self.getParam("DIA:RESUL:FLA?")

	def getDiagnosticLog(self):
		"""
		Return diagnostic test sequence results.

		:Returns: A comma-separated string containing the results of internal diagnostic routines.
		"""

		return self.getParam("DIA:RESUL:LOG?").strip()

	def getFirstError(self):
		"""
		Returns first message in error log.

		:Returns: a string describing an internal scope error, empty string if error queue is empty.
		"""

		return self.getParam("ERRLOG:FIRST?")

	def getNextError(self):
		"""
		Returns next message in error log.

		:Returns: a string describing an internal scope error, empty string if error queue is empty.
		"""

		return self.getParam("ERRLOG:NEXT?")

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

		return self.getParam("CURS?")


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

		return self.getParam("ALLE?")

	def isBusy(self):
		"""
		Check if the scope is busy.

		:Returns: 0 for not busy, 1 for busy.
		"""

		return int(self.getParam("BUSY?"))

	def clearStatus(self):
		"""
		Clears scope event queue and status registers.

		:Returns: True if command is successful, False otherwise.
		"""

		return self.getParam("*CLS?")

	def eventStatus(self):
		"""
		Check event status register.

		:Returns: the integer value held in the ESR.
		"""

		status = self.getParam("*ESR?")
		if status:
			return int(status)

	def eventCode(self):
		"""
		Get code of last event.

		:Returns: integer error code.
		"""

		return self.getParam("EVENT?")

	def eventMessage(self):
		"""
		Get message associated with last scope event.

		:Returns: event code and event message string, separated by a comma.
		"""

		return self.getParam("EVMSG?")

	"""
	END STATUS AND ERROR COMMANDS
	"""

	"""
	AUTOSET COMMAND
	"""

	def autoSet(self):

		return self.setParam("AUTOS EXEC")













