"""
Scope Finder
=================

Polls serial ports to find compatible oscilloscopes and returns them
as Oscilloscope objects.

"""

import visa # PyVisa
import oscilloscopes

class ScopeFinder:

	rm = visa.ResourceManager() # performs USB polling and finds instruments
	scopes = []

	def __init__(self):
		"""Constructor
		"""

		#  We only want USB scopes
		self.resources = self.rm.list_resources("USB?*")

		if(self.resources):
			self.instruments = []
			for resource in self.resources:
				self.instruments.append(self.rm.get_instrument(resource))
			for ins in self.instruments:
				info = self.query(ins, '*IDN?').split(',')
				if info[1] == 'TDS 2024B': # TDS 2024B oscilloscope
					info.append(info.pop().split()[1][3:]) # get our identification string into array format
					self.scopes.append(oscilloscopes.TDS2024B(ins, info[0],info[1],info[2],info[3]))
				# Support for other scopes to be implemented here!

	def query(self, inst, command):
		"""
		Issues query to instrument and returns response.

		Parameters:
			:inst: the instrument to be queried.
			:command: the command to be issued.

		:Returns: the response of inst.
		"""
		inst.write(command)
		return inst.read()

	def getScopes(self):
		"""
		Getter for array of connected oscilloscopes.

		:Returns: an array of PyVisa instrument objects representing USB oscilloscopes connected to the computer.
		"""
		return self.scopes
