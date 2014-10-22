"""
ScopeOut GUI

Defines GUI client that instantiates and controls widgets and threads.
"""

from PyQt5 import QtWidgets
from lib.scopeUtils import ScopeFinder as sf
from datetime import date, datetime
import sys, threading, os, time, numpy as np, lib.scopeWidgets as sw

class ThreadedClient(QtWidgets.QApplication):
	"""
	Launches the GUI and handles I/O.

	GUI components reside within the body of the class itself, while actual serial communication
	is in a separate thread.
	"""

	lock = threading.Lock()
	stopFlag = threading.Event()

	def __init__(self, *args):
		"""
		Constructor
		"""

		self.waveList = []

		QtWidgets.QApplication.__init__(self, *args)
		self.scopeControl = sw.scopeControlWidget(None)
		self.plot = sw.WavePlotWidget()
		self.waveCounter = QtWidgets.QLabel("Waveforms acquired: " + str(len(self.waveList)))
		self.mainWindow = sw.scopeOutMainWindow([self.plot,self.scopeControl,self.waveCounter],self.__closeEvent,self.__saveWaveformEvent)
		self.__connectSignals()

		self.scopeThread = threading.Thread(target=self.__scopeFind)
		self.scopeThread.start()

	def __connectSignals(self):
		"""
		Connects signals from subwidgets to appropriate slots.
		"""

		self.scopeControl.acqButton.clicked.connect(self.__acqEvent)
		self.scopeControl.channelComboBox.currentIndexChanged.connect(self.__setChannel)
		self.mainWindow.resetAction.triggered.connect(self.__resetEvent)

	def __acqEvent(self):
		"""
		Executed to collect waveform data from scope.
		"""

		self.acqThread = threading.Thread(target = self.__acqThread)
		self.acqThread.start()
		
	def __acqThread(self):

		if self.activeScope is not None :
			self.__status('Acquiring data...')

			if not self.multiAcq:

				self.lock.acquire()
		
				try:
					self.activeScope.makeWaveform()
					wave = self.activeScope.getNextWaveform()
					if wave['error'] is not None:
						self.waveList.append(wave);
						self.waveCounter.setText(("Waveforms acquired: " + str(len(self.waveList))))
				except AttributeError:
					wave = None
				finally:
					self.lock.release()

				if wave is not None and (not self.stopFlag.isSet()):
					if wave['error'] is not None:
						self.__status(wave['error'])
					else: 
						try:
							self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'])
							self.__status('Waveform acquired on ' +wave['dataChannel'])
						except KeyError:
							self.__status('Waveform not complete')
				else:
					self.__status('Error on Waveform Acquisition')

			else:

				for i in range(0,self.activeScope.numChannels):

					try:
						self.__setChannel(i)
						self.lock.acquire()
						self.activeScope.makeWaveform()
						wave = self.activeScope.getNextWaveform()
						if wave['error'] is not None:
							self.waveList.append(wave);
							self.waveCounter.setText(("Waveforms acquired: " + str(len(self.waveList))))
					except:
						wave = None
					finally:
						self.lock.release()					

					if wave is not None and (not self.stopFlag.isSet()):
						if wave['error'] is not None:
							self.__status(wave['error'])
						else: 
							try:
								self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'])
								self.__status('Waveform acquired on ' +wave['dataChannel'])
							except KeyError:
								self.__status('Waveform not complete')
					else:
						self.__status('Error on Waveform Acquisition')

				self.__status('Acquired all active channels.')


	def __scopeFind(self):
		"""
		Continually checks for connected scopes.
		"""
		showedMessage = False

		with sf() as finder:

			self.scopes = finder.refresh().getScopes()

			while not self.stopFlag.isSet():

				while not self.scopes: # Check for scopes and connect if possible
					if self.stopFlag.isSet():
						self.running = 0
						self.scopes = []
						break
					if not showedMessage:
						self.__status('No Oscilloscopes detected.')
						showedMessage = True
					self.lock.acquire()
					self.scopes = finder.refresh().getScopes()
					self.lock.release()

				if not self.stopFlag.isSet(): # Scope Found!
					self.activeScope = self.scopes[0]
					self.scopeControl.setScope(self.activeScope)
					self.__status('Found ' + str(self.activeScope))
					self.mainWindow.setEnabled(True)

				time.sleep(5)

				while self.scopes: # See if scope is still there or if program terminates
					if self.stopFlag.isSet():
						self.scopes = []
						break
					time.sleep(5)
					self.lock.acquire()
					if not finder.checkScope(0):
						self.scopes = []
					self.lock.release()

				self.__status('Connection to oscilloscope lost')
				self.activeScope = None
				self.scopeControl.setScope(self.activeScope)
		
	def __closeEvent(self):
		"""
		Executed on app close.
		"""
		print('Closing...')
		self.scopes = []
		self.stopFlag.set()
		self.closeAllWindows()
		self.beep()
		self.exit(0)
		print('Closed!')

	def __resetEvent(self):
		"""
		Called to reset waveform list and plot.
		"""

		self.waveList = []
		self.waveCounter.setText(("Waveforms acquired: " + str(len(self.waveList))))
		self.plot.resetPlot()
		self.__status('Data Reset.')

	def __setChannel(self,channel):
		"""
		Set data channel of active scope.

		Parameters:
			:channel: desired data channel
		"""
		def __channelThread():

			self.lock.acquire()
			if self.scopeControl.scope.setDataChannel(channel+1):
				self.__status('Data channel set to ' + str(channel + 1))
			else:
				self.__status('Failed to set data channel set to ' + str(channel + 1))
			self.lock.release()
			sys.exit(0)

		if (channel) in range(0,self.scopeControl.scope.numChannels):
			self.multiAcq = False
			threading.Thread(target=__channelThread).start()
		else:
			self.__status("Selected all data channels")
			self.multiAcq = True

	def __saveWaveformEvent(self):
		"""
		Called in order to save in-memory waveforms to disk.
		"""
		if self.waveList:

			try:
				waveDirectory = os.path.join(os.getcwd(), 'waveforms')
				if not os.path.exists(waveDirectory):
					os.makedirs(waveDirectory)

				dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
				if not os.path.exists(dayDirectory):
					os.makedirs(dayDirectory)

				filename = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S')+'.csv'
				saveFile = open(os.path.join(dayDirectory,filename).replace('\\','/'),'w')

				for wave in self.waveList:
					self.__writeWave(saveFile,wave)

				saveFile.close()
				self.__status('Waveform saved to ' + filename)

			except Exception as e:
				print(e)

		else:
			self.__status('No Waveforms to Save')

	def __writeWave(self, outFile, wave):
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
					print('X and Y data incompatible.')

			outFile.write('\n')

		except Exception as e:
			print(e)

	def __status(self, message):
		"""
		Print a message to the statusbar.

		Parameters:
			:message: The string to be printed.
		"""

		self.mainWindow.statusBar().showMessage(message)


 



