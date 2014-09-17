"""
Oscilloscope
================

Classes to represent, control, and read out VISA Oscilloscopes.
"""

import visa, numpy as np, matplotlib.pyplot as plt

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

	def query(self, command):
		"""
		Issues query to scope and returns output.

		Parameters:
			:command: command to be written to scope.

		:Returns: the output of the scope given in response to command.
		"""

		try:
			self.scope.write(command)
			return self.scope.read().strip()
		except Exception:
			print(Exception)
			pass

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
			print("VISA Error: Command timed out.")

class TDS2024B(GenericOscilloscope):
	"""
	Class representing Tektronix 2024B.
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

		self.make = make
		self.model = model
		self.serialNumber = serialNum
		self.firmwareVersion = firmware
		self.waveformSetup()
		
	def waveformSetup(self):
		"""
		Acquires and stores all necessary parameters for waveform transfer and display.
		"""

		self.dataChannel = self.query("DAT:SOU?")
		preamble = self.query("WFMP?").split(';')
		self.dataWidth = int(preamble[0])
		self.bitsPerPoint = int(preamble[1])
		self.encoding = preamble[2]
		self.binaryFormat = preamble[3]
		self.sigBit = preamble[4]
		self.numberOfPoints = int(preamble[5])
		self.pointFormat = preamble[7]
		self.xIncr = float(preamble[8])
		self.xOff = float(preamble[9])
		self.xZero = float(preamble[10])
		self.xUnit = preamble[11].strip('"')
		if self.xUnit == 's':
			self.xUnit = 'Seconds'
		self.yMult = float(preamble[12])
		self.yZero = float(preamble[13])
		self.yOff = float(preamble[14])
		self.yUnit = preamble[15].strip('"')

	def __str__(self):
		"""
		Object to String.
		"""
		return "{:s} {:s} Oscilloscope. Serial Number: {:s}. Output on {:s} in {:s} format.".format(self.make,self.model,self.serialNumber,self.dataChannel,self.encoding)

	def getWaveform(self):
		"""
		Acquire entire waveform, both preamble and curve data.

		:Returns: a semicolon-separated preamble followd by a comma-separated list of raw ADC levels.
		"""
		try:
			return self.query("WAVF?")
		except AttributeError:
			print("Error acquiring waveform data.")
			pass

	def getCurve(self):
		"""
		Set up waveform acquisition and get curve data.

		:Returns: a list of voltage values describing a captured waveform.
		"""

		self.waveformSetup()

		try:
			curveData = self.query("CURV?").split(',')
			curveData = list(map(int,curveData))
			for i in range(0,len(curveData)):
				curveData[i] = self.yZero +self.yMult*(curveData[i]-self.yOff)
			return curveData

		except AttributeError:
			print("Error acquiring waveform data.")
			pass

		

	def plotCurve(self):
		"""
		Create and display a pyplot of captured waveform.
		"""

		curve = self.getCurve()
		xArray = np.arange(0,self.numberOfPoints*self.xIncr,self.xIncr)
		unitSet = self.autosetUnits(xArray)
		xArray = unitSet[0]
		self.xUnit = unitSet[1] + self.xUnit
		unitSet = self.autosetUnits(curve)
		curve = unitSet[0]
		self.yUnit = unitSet[1] + self.yUnit
		plt.plot(xArray,curve)
		plt.title("Waveform Capture")
		plt.ylabel(self.yUnit)
		plt.xlabel(self.xUnit)
		plt.show()

	def autosetUnits(self, axisArray):
		"""
		Set the X units of the pyplot to the correct size based on the values in axisArray.

		Parameters:
			:axisArray: the array of values representing one dimension of the waveform.
		"""
		xMax = np.amax(axisArray)
		if xMax > 1e-9:
			prefix = 'nano'
			if xMax > 1e-6:
				prefix = 'micro'
				if xMax > 1e-3:
					prefix = 'milii'
					if xMax > 1:
						prefix = ''
						return [axisArray,prefix]
					axisArray = np.multiply(axisArray,1000)
					return [axisArray,prefix]
				axisArray = np.multiply(axisArray,1e6)
				return [axisArray,prefix]
			axisArray = np.multiply(axisArray,1e9)

		return [axisArray,prefix]

	def checkTrigger(self):
		"""
		Read trigger status of TDS2024B.

		:Returns: a string describing trigger status: {AUTO | READY | TRIGGER}
		"""

		try:
			return self.query("TRIG:STATE?")
		except:
			pass



