"""
ScopeOut GUI

Defines GUI client that instantiates and controls widgets and threads.
"""

from PyQt5 import QtWidgets, QtCore
from lib.scopeUtils import ScopeFinder as sf
from lib.oscilloscopes import GenericOscilloscope
from datetime import date, datetime
from functools import partial
import sys, threading, os, time, logging, numpy as np, lib.scopeWidgets as sw, lib.waveUtils as WU

class ThreadedClient(QtWidgets.QApplication):
	"""
	Launches the GUI and handles I/O.

	GUI components reside within the body of the class itself, while actual serial communication
	is in a separate thread.
	"""

	lock = threading.Lock()
	stopFlag = threading.Event()
	channelSetFlag = threading.Event()
	continuousFlag = threading.Event()
	continuousFlag.set()
	statusChange = QtCore.pyqtSignal(str)
	scopeChange = QtCore.pyqtSignal(GenericOscilloscope)
	
	def __init__(self, *args):
		"""
		Constructor
		"""
		QtWidgets.QApplication.__init__(self, *args)

		# create logger
		self.logger = logging.getLogger('ScopeOut.ThreadedClient')
		self.logger.setLevel(logging.DEBUG)

		self.logger.info("Threaded Client initialized")

		self.waveList = []

		self.scopeControl = sw.scopeControlWidget(None)
		self.plot = sw.WavePlotWidget()
		self.waveOptions = sw.waveOptionsWidget()
		
		self.logger.info("All Widgets initialized")

		self.mainWindow = sw.ScopeOutMainWindow([self.plot,self.scopeControl,self.waveOptions],self.__closeEvent,self.__saveWaveformEvent)

		self.__connectSignals()
			
		scopeFinderThread = threading.Thread(target=self.__scopeFind, name='ScopeFind')
		scopeFinderThread.start()

		self.checkTimer = threading.Timer(5.0, self.__scopeCheck)

		self.mainWindow.show()

	def __connectSignals(self):
		"""
		Connects signals from subwidgets to appropriate slots.
		"""

		self.scopeControl.acqButton.clicked.connect(partial(self.__acqEvent,'now'))
		self.scopeControl.acqOnTrigButton.clicked.connect(partial(self.__acqEvent,'trig'))
		self.scopeControl.channelComboBox.currentIndexChanged.connect(self.__setChannel)
		self.scopeControl.autoSetButton.clicked.connect(self.__autosetEvent)
		self.mainWindow.resetAction.triggered.connect(self.__resetEvent)
		self.statusChange.connect(self.mainWindow.status)
		self.scopeChange.connect(self.scopeControl.setScope)
		self.logger.info("Signals connected")

	def __acqEvent(self, mode):
		"""
		Executed to collect waveform data from scope.
		"""
		def plotHeld():
			"""
			Check if 'plot hold' option is selected.
			
			:Returns: True if plot is to be held, false otherwise
			"""

			held = self.scopeControl.plotHeld()
			return held

		def __immAcqThread():

			self.channelSetFlag.clear()

			if self.activeScope is not None :
				self.__status('Acquiring data...')

				if not self.multiAcq:

					self.logger.info("Single channel acquisition")
			
					try:
						self.lock.acquire()
						self.activeScope.makeWaveform()
						wave = self.activeScope.getNextWaveform()
					except AttributeError:
						wave = None
					finally:
						if self.lock.locked():
							self.lock.release()

					if wave is not None and (not self.stopFlag.isSet()):
						if wave['error'] is not None:
							self.logger.debug("Wave error: %s", wave['error'])
							self.__status(wave['error'])
						else:
							try:
								self.logger.info("Successfully acquired waveform from %s", wave['dataChannel'])
								self.__status('Waveform acquired on ' +wave['dataChannel'])
								start, end = WU.findPeakEnds(wave, self.waveOptions.getThresholds()[0], self.waveOptions.getThresholds()[1])
								wave['peakStart'] = start
								wave['peakEnd'] = end
								self.waveList.append(wave);
								self.__waveCount(len(self.waveList))
								self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'],plotHeld())
								if self.waveOptions.peakStart():
									self.plot.vertLines([wave['peakStart'],wave['peakEnd']])
							except Exception as e:
								self.__status('Error occurred during wave plotting. Check log for details.')
								self.logger.error(e)
					else:
						self.__status('Error on Waveform Acquisition')

				else:
					self.logger.info("Multichannel acquisition")

					self.plot.resetPlot()

					for i in range(0,self.activeScope.numChannels):

						try:
							self.logger.info("Acquiring data from channel %d", i+1)
							self.__setChannel(i)
							self.channelSetFlag.wait()
							self.lock.acquire()
							self.activeScope.makeWaveform()
							self.lock.release()
							wave = self.activeScope.getNextWaveform()
							if wave['error'] is None:
								self.logger.info("Successfully acquired waveform from %s", wave['dataChannel'])
								self.waveList.append(wave);
								self.__waveCount(len(self.waveList))
						except Exception as e:
							self.logger.error(e)
							wave = None
						finally:
							if self.lock.locked():
								self.lock.release()				

						if wave is not None and (not self.stopFlag.isSet()):
							if wave['error'] is not None:
								self.__status(wave['error'])
							else: 
								try:
									self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'],True)
									self.__status('Waveform acquired on ' +wave['dataChannel'])
								except KeyError:
									self.__status('Waveform not complete')
						else:
							self.__status('Error on Waveform Acquisition')

					self.__status('Acquired all active channels.')
					self.multiAcq = True
					self.mainWindow.update()

		def __trigAcqThread():

			self.__status("Waiting for trigger...")
			self.lock.acquire()
			trigState = self.activeScope.checkTrigger()
			
			while trigState != 'TRIGGER' and not self.stopFlag.isSet():
				trigState = self.activeScope.checkTrigger()

			try:
				self.activeScope.makeWaveform()
				wave = self.activeScope.getNextWaveform()
				if wave['error'] is None:
					self.logger.info("Successfully acquired waveform from %s", wave['dataChannel'])
					self.waveList.append(wave);
					self.__waveCount(len(self.waveList))
			except AttributeError:
				wave = None
			finally:
				if self.lock.locked():
					self.lock.release()

			if wave is not None and (not self.stopFlag.isSet()):
				if wave['error'] is not None:
					self.__status(wave['error'])
				else: 
					try:
						self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'],plotHeld)
						self.__status('Waveform acquired on ' +wave['dataChannel'])
					except KeyError:
						self.__status('Waveform not complete')
			else:
				self.__status('Error on Waveform Acquisition')

		if mode == 'now':
			self.logger.info("Immediate acquisition Event")
			acqThread = threading.Thread(target = __immAcqThread)
		elif mode == 'trig':
			self.logger.info("Acquisition on trigger event")
			acqThread = threading.Thread(target=__trigAcqThread)
		
		acqThread.start()

	def __scopeFind(self):
		"""
		Continually checks for connected scopes, until one is found, then begins periodic checking.
		"""

		self.logger.info("Scope acquisition thread started")

		while not self.stopFlag.isSet():

			if self.continuousFlag.isSet():

				with sf() as self.finder:

					self.logger.info("Entered continuous checking mode")

					while self.continuousFlag.isSet() and not self.stopFlag.isSet():

						showedMessage = False

						self.scopes = self.finder.refresh().getScopes()

						while not self.scopes: # Check for scopes and connect if possible
							if self.stopFlag.isSet():
								self.scopes = []
								break
							if not showedMessage:
								self.__status('No Oscilloscopes detected.')
								showedMessage = True
							self.lock.acquire()
							self.scopes = self.finder.refresh().getScopes()
							self.lock.release()

						if not self.stopFlag.isSet(): # Scope Found!
							self.activeScope = self.scopes[0]
							self.logger.info("Set active scope to %s", str(self.activeScope))
							self.scopeChange.emit(self.activeScope)
							self.__status('Found ' + str(self.activeScope))
							self.mainWindow.setEnabled(True)
							self.continuousFlag.clear()
							self.checkTimer.start()

		self.logger.info("Scope acquisition Thread ended")

	def __scopeCheck(self):
		"""
		Periodically confirms that scopes are still connected.
		"""
		if not self.stopFlag.isSet():
			self.lock.acquire()
			connected = self.finder.checkScope(0)
			self.lock.release()
			if not connected:
				self.scopes = []
				self.logger.info("Lost Connection to Oscilloscope(s)")
				self.__status("Lost Connection to Oscilloscope(s)")
				self.mainWindow.setEnabled(False)
				self.continuousFlag.set()
				self.checkTimer.cancel()
			elif not self.stopFlag.isSet():
				self.checkTimer = threading.Timer(5.0, self.__scopeCheck)
				self.checkTimer.start()

	def __closeEvent(self):
		"""
		Executed on app close.
		"""

		self.scopes = []
		self.stopFlag.set()
		self.continuousFlag.clear()
		self.checkTimer.cancel()
		self.quit()

	def __resetEvent(self):
		"""
		Called to reset waveform list and plot.
		"""

		self.waveList = []
		self.__waveCount(len(self.waveList))
		self.plot.resetPlot()
		self.__status('Data Reset.')

	def __setChannel(self,channel):
		"""
		Set data channel of active scope.

		Parameters:
			:channel: desired data channel
		"""
		def __channelThread():

			try:
				self.lock.acquire()
				if self.scopeControl.scope.setDataChannel(channel+1):
					self.logger.info('Successfully set data channel %d', channel+1)
					self.__status('Data channel set to ' + str(channel + 1))
				else:
					self.logger.debug('Failed to set data channel set to ' + str(channel + 1))
					self.__status('Failed to set data channel ' + str(channel + 1))
			except Exception as e:
				self.logger.error(e)
			finally:
				try:
					self.channelSetFlag.set()
					if self.lock.locked():
						self.lock.release()
				except Exception as e:
					logger.error(e)

		self.channelSetFlag.clear()
		self.logger.info('Attempting to set data channel %d', channel+1)
		if channel in range(0,self.scopeControl.scope.numChannels):
			self.multiAcq = False
			setThread = threading.Thread(target=__channelThread)
			setThread.start()
		else:
			self.logger.info("Selected all data channels")
			self.__status("Selected all data channels")
			self.multiAcq = True

	def __saveWaveformEvent(self):
		"""
		Called in order to save in-memory waveforms to disk.
		"""

		def __writeWave(outFile, wave):
			"""
			Write contents of waveform dictionary to .csv file.
			
			Parameters:
				:outFile: Open file object to be written to.
				:wave: full waveform dictionary.
			"""

			try:
				outFile.write('"Waveform captured ' + datetime.now().isoformat() + ' from ' + str(self.activeScope)+'"\n')
				outFile.write('\n')
				for field in wave:
					if not isinstance(wave[field],(list,np.ndarray)):
						outFile.write('"' + field + '",' + str(wave[field]))
						outFile.write('\n')
				outFile.write('\n')
				outFile.write('X,Y\n')
				for i in range(0,len(wave['xData'])):
					try:
						outFile.write(str(wave['xData'][i])+','+str(wave['yData'][i])+'\n')
					except IndexError:
						self.logger.error('X and Y data incompatible.')

				outFile.write('\n')

			except Exception as e:
				self.logger.error(e)

		if self.waveList:

			try:
				waveDirectory = os.path.join(os.getcwd(), 'waveforms')
				if not os.path.exists(waveDirectory):
					os.makedirs(waveDirectory)

				dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
				if not os.path.exists(dayDirectory):
					os.makedirs(dayDirectory)

				filename = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S')+'.csv'

				with open(os.path.join(dayDirectory,filename).replace('\\','/'),'w') as saveFile:
					for wave in self.waveList:
						__writeWave(saveFile,wave)

				self.logger.info("%d waveforms saved to %s", len(self.waveList), filename)
				self.__status('Waveform saved to ' + filename)

			except Exception as e:
				self.logger.error(e)

		else:
			self.__status('No Waveforms to Save')

	def __status(self, message):
		"""
		Print a message to the statusbar.

		Parameters:
			:message: The string to be printed.
		"""

		self.statusChange.emit(message)

	def __autosetEvent(self):
		"""
		Called when a scope autoset is requested.
		"""

		def __doAutoset():
			"""
			Thread to execute the autoset.
			"""

			self.lock.acquire()
			self.scopeControl.scope.autoSet()
			self.lock.release()

		self.logger.info("Starting autoSet")
		self.__status("Executing Auto-set. Ensure process is complete before continuing.")
		threading.Thread(target = __doAutoset, name = 'AutoSetThread').start()

	def __waveCount(self, waves):

		self.waveOptions.updateCount(waves)