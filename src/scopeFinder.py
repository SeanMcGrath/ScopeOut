"""
Scope Finder
=================

Polls serial ports to find compatible oscilloscopes and returns them
as Oscilloscope objects.

"""

import visa # PyVisa
from oscilloscope import Oscilloscope

class ScopeFinder:

	rm = visa.ResourceManager() # performs USB polling and finds instruments

	def __init__(self):

		#  We only want USB scopes
		self.resources = self.rm.list_resources("USB?*")

		if(self.resources):
			self.instruments = []
			self.scopes = []
			for resource in self.resources:
				self.instruments.append(self.rm.get_instrument(resource))
			for ins in self.instruments:
				info = self.query(ins, '*IDN?').split(',')
				if info[1] == 'TDS 2024B': # TDS 2024B oscilloscope
					info.append(info.pop().split()[1][3:]) # get our identification string into array format
					self.scopes.append(Oscilloscope(ins, info[0],info[1],info[2],info[3]))
				# Support for other scopes implemented here!

	def query(self, inst, command):
		inst.write(command)
		return inst.read()

	def getScopes(self):
		return self.scopes
