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
		self.scope.write(command)
		return self.scope.read()