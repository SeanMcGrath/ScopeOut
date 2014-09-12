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
			:brand: brand of scope
			:model: model of scope
			:serial: serial number of scope
			:firmware: scope firmware version
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
			return self.scope.read()
		except:
			print("VISA handle not valid!")
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
		return self.scope.read()

class TDS2024B(GenericOscilloscope):
	"""
	Class representing Tektronix 2024B.
	"""

	def __init__(self, VISA, make, model, serialNum, firmware):
		"""
		Constructor.

		"""

		
