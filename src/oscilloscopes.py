"""
Oscilloscope
================

Classes to represent, control, and read out VISA Oscilloscopes.
"""

import visa

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

		self.dataSource = self.query("DAT:SOU?")
		preamble = self.query("WFMP?").split(';')
		self.BYT_Nr = preamble[0]
		self.BIT_Nr = preamble[1]
		self.encoding = preamble[2]
		self.binaryFormat = preamble[3]
		self.sigBit = preamble[4]
		self.numberOfPoints = preamble[5]
		self.pointFormat = preamble[7]

