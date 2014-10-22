"""
Scope Finder
=================

Polls serial ports to find compatible oscilloscopes and returns them
as Oscilloscope objects.

"""

import visa # PyVisa
import logging
import lib.oscilloscopes as oscilloscopes

class ScopeFinder:


	def __init__(self):
		"""Constructor
		"""
		self.logger = logging.getLogger('ScopeOut.scopeUtils.ScopeFinder')
		self.logger.info("ScopeFinder Initialized")

		self.rm = visa.ResourceManager() # performs USB polling and finds instruments

		self.refresh()

	def __enter__(self):
		return self

	def __exit__(self,type,value,traceback):
		pass

	def query(self, inst, command):
		"""
		Issues query to instrument and returns response.

		Parameters:
			:inst: the instrument to be queried.
			:command: the command to be issued.

		:Returns: the response of inst as a string.
		"""
		inst.write(command)
		return inst.read().strip() # strip newline

	def getScopes(self):
		"""
		Getter for array of connected oscilloscopes.

		:Returns: an array of PyVisa instrument objects representing USB oscilloscopes connected to the computer.
		"""

		return self.scopes

	def refresh(self):
		"""
		Re-run scope acquisition to update scope array.
		"""

		self.scopes = []
		self.resources = []

		try:
			self.resources = self.rm.list_resources("USB?*") #  We only want USB scopes
		except visa.VisaIOError:
			pass
			
		if(self.resources):
			self.logger.info("%d VISA Resources found", len(self.resources))
			self.instruments = []
			for resource in self.resources:
				self.instruments.append(self.rm.get_instrument(resource))
			for ins in self.instruments:

				try:
					info = self.query(ins, '*IDN?').split(',') # Parse identification string

					if info[1] == 'TDS 2024B': # TDS 2024B oscilloscope
						info.append(info.pop().split()[1][3:]) # get our identification string into array format
						scope = oscilloscopes.TDS2024B(ins, info[0],info[1],info[2],info[3])
						self.scopes.append(scope)
						self.logger.info("Found %s", str(scope))
					
					# Support for other scopes to be implemented here!
				except visa.VisaIOError as e:
					self.logger.error(e)
		return self

	def checkScope(self, scopeIndex):
		"""
		Check if the scope at scopeIndex is still connected.
		"""

		try:
			if self.scopes[scopeIndex].query("TRIGGER?"):
				return True
			else:
				return False
		except:
			return False
