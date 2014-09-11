"""
Oscilloscope
================

Class to represent, control, and read out a VISA Oscilloscope.
"""

import visa

class Oscilloscope:

	def __init__(self, VISA, brand, model, serial=0, firmware="v0"):
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
		self.brand = brand
		self.model = model
		self.serialNumber = serial
		self.firmware = firmware

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