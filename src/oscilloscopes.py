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
		Acquires and stores all encessary parameters for waveform transfer and display.
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

		return self.query("WAVF?")

	def getCurve(self):

		self.waveformSetup()

		try:
			curveData = self.query("CURV?").split(',')
			curveData = list(map(int,curveData))
			for i in range(0,len(curveData)):
				curveData[i] = self.yZero +self.yMult*(curveData[i]-self.yOff)
		except AttributeError:
			print("Error acquiring waveform data.")
			pass

		return curveData

	def plotCurve(self):

		curve = self.getCurve()
		xArray = np.arange(0,self.numberOfPoints*self.xIncr,self.xIncr)
		plt.plot(xArray,curve)
		plt.title("Waveform Capture")
		plt.ylabel(self.yUnit)
		plt.show()
		return
