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

	GUI components reside within the body of the class itself. This client acquires and manipulates
	data from attached scopes and feeds it to the GUI. Various threads are created to carry out
	USB communication asynchronously.

	NOTES:
		Initially, the client is not connected to any scopes, and searches for them continuously.
		This occurs in the scopeFind thread. when a scope is found, this thread returns, and
		periodic scope checking begins in the scopeCheck thread. A loss of connection should disable
		the interface and initiate scopeFind again.

		Creation of the widgets that make up the actual interface is done in the constructor of this 
		class. All Qt Signals that facilitate the interaction of the client with these widgets are
		connected in the __connectSignals method.

		The actions of GUI components that interact with scopes and their data occur in the "event"
		methods of this client.

		It is essential that the Qt "signaling" mechanism be used to interact between threads
		(The GUI is considered a thread indpendent of this client). Directly modifying the
		appearance or contents of a GUI widget can cause a program crash; instead, emit the data
		you wish to send as a signal which the widget will receive safely.
	"""

	lock = threading.Lock() # Lock for scope resource
	stopFlag = threading.Event() # Event representing termination of program
	acqStopFlag = threading.Event() # Event representing termination of continuous acquisition
	channelSetFlag = threading.Event() # Set when data channel has been successfully changed.
	continuousFlag = threading.Event() # Set while program is finding scopes continuously
	continuousFlag.set()
	acquireFlag = threading.Event() # Set during continuous acquisition when a waveform has been acquired.
	statusChange = QtCore.pyqtSignal(str) # Signal sent to GUI waveform counter.
	scopeChange = QtCore.pyqtSignal(GenericOscilloscope) # Signal sent to change the active oscilloscope.
	
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
		self.integralList = []
		self.histMode = False

		self.acqControl = sw.acqControlWidget(None)
		self.plot = sw.WavePlotWidget()
		self.waveOptions = sw.waveOptionsTabWidget()
		
		self.logger.info("All Widgets initialized")

		widgets = [self.plot,self.acqControl,self.waveOptions]
		self.mainWindow = sw.ScopeOutMainWindow(widgets,self.__closeEvent,self.__saveWaveformEvent)

		self.__connectSignals()
			
		scopeFinderThread = threading.Thread(target=self.__scopeFind, name='ScopeFind')
		scopeFinderThread.start()

		self.mainWindow.show()

	def __connectSignals(self):
		"""
		Connects signals from subwidgets to appropriate slots.
		"""

		self.acqControl.acqButton.clicked.connect(partial(self.__acqEvent,'now'))
		self.acqControl.acqOnTrigButton.clicked.connect(partial(self.__acqEvent,'trig'))
		self.acqControl.contAcqButton.clicked.connect(partial(self.__acqEvent,'cont'))
		self.acqControl.channelComboBox.currentIndexChanged.connect(self.__setChannel)
		self.acqControl.autoSetButton.clicked.connect(self.__autosetEvent)
		self.acqControl.acqStopButton.clicked.connect(self.acqStopFlag.set)
		self.mainWindow.resetAction.triggered.connect(self.__resetEvent)
		self.statusChange.connect(self.mainWindow.status)
		self.scopeChange.connect(self.acqControl.setScope)
		self.logger.info("Signals connected")

	def __acqEvent(self, mode):
		"""
		Executed to collect waveform data from scope.
		"""

		def peakFindMode():
			"""
			Determine the desired method of peak detection from the status of the tab options widget.
			"""
			mode = self.waveOptions.getMode()
			return mode

		def plotHeld():
			"""
			Check if 'plot hold' option is selected.
			
			:Returns: True if plot is to be held, false otherwise
			"""

			held = self.acqControl.plotHeld()
			return held

		def processWave(wave):
			"""
			Run desired calculations on acquired wave and display plots.

			Parameters:
				:wave: The dictionary containing waveform information.
			"""

			if wave['error'] is not None:
				self.logger.error("Wave error: %s", wave['error'])
				self.__status(wave['error'])
			else:
				try:
					self.logger.info("Successfully acquired waveform from %s", wave['dataChannel'])
					self.__status('Waveform acquired on ' +wave['dataChannel'])
					if not self.__histogramMode():
						self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'],plotHeld())
					if peakFindMode() == 'Smart':
						start, end = WU.smartFindPeakEnds(wave, self.waveOptions.getParameters())
					elif peakFindMode() == 'Fixed':
						start, end = WU.fixedFindPeakEnds(wave, self.waveOptions.getParameters())
					wave['peakStart'] = start
					wave['peakEnd'] = end
					integral = WU.integratePeak(wave)
					wave['peakIntegral'] = integral
					self.integralList.append(integral)
					if self.__histogramMode() and len(self.integralList)>1:
						self.plot.showHist(self.integralList)
					self.waveList.append(wave)
					self.__waveCount(len(self.waveList))
					if self.waveOptions.peakStart() and start >= 0 and not self.__histogramMode():
						self.plot.vertLines([ wave['xData'][start], wave['xData'][end] ])
				except Exception as e:
					self.__status('Error occurred during wave plotting. Check log for details.')
					self.logger.error(e)

		def __immAcqThread():
			"""
			Contains instructions for acquiring and storing waveforms ASAP.
			self.multiAcq serves as the flag to intiate multi-channel acquisition.
			"""

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
						processWave(wave)
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
						except Exception as e:
							self.logger.error(e)
							wave = None
						finally:
							if self.lock.locked():
								self.lock.release()				

						if wave is not None and (not self.stopFlag.isSet()):
							processWave(wave)
						else:
							self.__status('Error on Waveform Acquisition')

					self.__status('Acquired all active channels.')
					self.multiAcq = True
					self.mainWindow.update()

		def __trigAcqThread():
			"""
			Waits for the scope to trigger, then acquires and stores waveforms in the same way as immAcq.
			"""

			self.lock.acquire()
			trigState = self.activeScope.checkTrigger()
			
			while trigState != 'TRIGGER' and not self.stopFlag.isSet():
				trigState = self.activeScope.checkTrigger()

			try:
				self.activeScope.makeWaveform()
				wave = self.activeScope.getNextWaveform()
			except AttributeError:
				wave = None
			finally:
				self.acquireFlag.set()
				if self.lock.locked():
					self.lock.release()

			if wave is not None and (not self.stopFlag.isSet()):
				processWave(wave)
			else:
				self.__status('Error on Waveform Acquisition')

		def __contAcqThread():
			"""
			Continually runs trigAcqThread until the stop signal is received.
			"""

			self.acqControl.contAcqButton.setEnabled(False)

			while not self.stopFlag.isSet() and not self.acqStopFlag.isSet():
				self.acquireFlag.wait()
				acqThread = threading.Thread(target=__trigAcqThread)
				acqThread.start()
				self.acquireFlag.clear()

			self.acqStopFlag.clear()
			self.__status("Continuous Acquisiton Halted.")
			self.acqControl.contAcqButton.setEnabled(True)


		if mode == 'now': # Single, Immediate acquisition
			self.logger.info("Immediate acquisition Event")
			acqThread = threading.Thread(target = __immAcqThread)
			acqThread.start()

		elif mode == 'trig': # Acquire on trigger
			self.__status("Waiting for trigger...")
			self.logger.info("Acquisition on trigger event")
			acqThread = threading.Thread(target=__trigAcqThread)
			acqThread.start()

		elif mode == 'cont': # Continuous Acquisiton
			self.logger.info('Continuous Acquisition Event')
			self.__status("Acquiring Continuously...")
			self.acquireFlag.set()
			acqThread = threading.Thread(target = __contAcqThread)
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
							self.checkTimer = threading.Timer(5.0, self.__scopeCheck)
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
		self.integralList = []
		self.__waveCount(0)
		self.plot.resetPlot()
		self.__status('Data Reset.')

	def __setChannel(self,channel):
		"""
		Set data channel of active scope.

		Parameters:
			:channel: desired data channel
		"""

		channels = self.acqControl.getChannels()
		print(channels[channel])

		def __channelThread():

			try:
				self.lock.acquire()
				if self.acqControl.scope.setDataChannel(channels[channel]):
					self.logger.info('Successfully set data channel %s', channels[channel])
					self.__status('Data channel set to ' + channels[channel])
				else:
					self.logger.debug('Failed to set data channel set to ' + channels[channel])
					self.__status('Failed to set data channel ' + channels[channel])
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
		self.logger.info('Attempting to set data channel %s', channels[channel])
		if channel in range(0,self.acqControl.scope.numChannels):
			self.multiAcq = False
			setThread = threading.Thread(target=__channelThread)
			setThread.start()
		elif channels[channel] == 'All':
			self.logger.info("Selected all data channels")
			self.__status("Selected all data channels")
			self.multiAcq = True
		elif channels[channel] == 'Math':
			self.logger.info("selected Math data channel")
			self.__status("selected Math data channel")
			self.multiAcq = False
			setThread = threading.Thread(target=__channelThread)
			setThread.start()

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
			self.acqControl.scope.autoSet()
			self.lock.release()

		self.logger.info("Starting autoSet")
		self.__status("Executing Auto-set. Ensure process is complete before continuing.")
		threading.Thread(target = __doAutoset, name = 'AutoSetThread').start()

	def __waveCount(self, waves):

		self.waveOptions.updateCount(waves)

	def __histogramMode(self):
		"""
		Check whether to display histogram or wave plot.
		"""

		return self.mainWindow.histogramModeAction.isChecked()
