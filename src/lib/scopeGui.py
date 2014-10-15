"""
ScopeOut GUI

File to define relevant classes and widgets for user interface.
"""

from PyQt5 import QtGui, QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from lib.scopeUtils import ScopeFinder as sf
from lib.oscilloscopes import GenericOscilloscope
from queue import Queue
from datetime import date, datetime
import sys, threading, re, os, functools, time, numpy as np

class scopeOutMainWindow(QtWidgets.QMainWindow):
	"""
	Class to represent entire GUI Window. Will contain various QWidgets within a QLayout,
	menu bars, tool bars, etc.
	"""

	def __init__(self, widgets, endCommand, saveCommand, *args):
		"""
		Constructor.
		will be passed widgets from threaded client (probably as array).
		"""
		self.widgets = widgets
		self.endCommand = endCommand
		self.saveCommand = saveCommand

		QtWidgets.QMainWindow.__init__(self, *args)

		self.central = QtWidgets.QWidget(self)
		self.layout = QtWidgets.QGridLayout(self.central)
		self.layout.addWidget(self.widgets[0],0,0)
		self.layout.addWidget(self.widgets[1],0,1)
		self.central.setLayout(self.layout)
		self.setCentralWidget(self.central)

		self.initUI()

	def initUI(self):
		"""
		Construct non-widget UI elements - Menubar, statusbar, etc. Load theme
		"""

		self.initTheme()

		# File->Exit
		exitAction = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)        
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.closeEvent)

        # Graph->Reset
		saveAction = QtWidgets.QAction(QtGui.QIcon('save.png'), '&Save Waveform', self)
		saveAction.setShortcut('Ctrl+S')
		saveAction.setStatusTip('Save Waveform to .csv file')
		saveAction.triggered.connect(self.saveCommand)

        # Put title on window
		self.setWindowTitle('ScopeOut')

        # Initialize status bar at bottom of window
		self.statusBar().showMessage("Initializing")

        # Initialize "File" Section of top menu
		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(exitAction)
		fileMenu.addAction(saveAction)
		viewMenu = menubar.addMenu('&View')
		themeMenu = viewMenu.addMenu('Change Theme')
		if self.themes:
			themeActions = []
			for theme in self.themes:
				themeAction = QtWidgets.QAction(theme.split('\\')[-1].split('.')[0],self)
				themeAction.setStatusTip('Change active theme to ' + theme.split('\\')[-1].split('.')[0])
				themeAction.triggered.connect(functools.partial(self.loadTheme,theme))
				themeActions.append(themeAction)
				themeAction = None
			for theme in themeActions:
				themeMenu.addAction(theme)
		else:
			themeMenu.setEnabled(False)

	def initTheme(self):
		"""
		Finds all themes, and loads first available one.
		"""
		if self.findThemes():
			i = 0
			while True:
				if i > len(self.themes) - 1:
					break
				elif self.loadTheme(self.themes[i]):
					break
				else:
					i += 1

	def findThemes(self):
		"""
		Finds themes (stylesheets) in the Themes folder, currently '\lib\Themes'
		and stores their paths in self.themes.

		:Returns: self.themes, the array of theme paths, for convenience.
		"""
		path = os.path.join(os.getcwd(), 'lib\Themes')
		self.themes = []

		try:
			themeFiles = os.listdir(path)
			for theme in themeFiles:
				if re.match('.*stylesheet',theme):
					try:
						openTheme = os.path.join(path,theme)
						self.themes.append(openTheme)
					except Exception as e:
						print('Could not process ' + theme + ', ignoring')
		except Exception as e:
			print('No themes folder found')

		return self.themes

	def loadTheme(self, themePath):
		"""
		Loads style sheet from themePath and sets it as the application's style.

		:Returns: True if theme is loaded successfully, False otherwise.
		"""

		try:
			style = open(themePath,'r')
			self.setStyleSheet('')
			self.setStyleSheet(style.read())
			self.repaint()
		except Exception as e:
			print(themePath + ' could not be loaded')
			return False

		return True
    
	def closeEvent(self, ev):
		"""
		Executed when window is closed or File->Exit is called.

		:ev:
			The CloseEvent in question. This is accepted by default.
		"""
		for widget in self.widgets:
			widget.close()
		self.endCommand()

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		for widget in self.widgets:
			widget.setEnabled(bool)

class WavePlotWidget(FigureCanvas):
	"""
	Class to hold matplotlib Figures for display.
	"""

	def __init__(self):
		self.fig = Figure()
		self.fig.suptitle("Waveform Capture")
		self.axes = self.fig.add_subplot(111)
		FigureCanvas.__init__(self,self.fig) 
		self.show()

	def showPlot(self, xData, xLabel, yData, yLabel):
		'''
		Fill plot with data and draw it on the screen.

		:xData:
		    X data for plot (usually time)

		:xLabel:
			string to label x axis.

		:yData:
		    Y data for plot.

		:yLabel:
			string to label y axis

		'''

		self.axes.clear()
		xData, xPrefix = self.autosetUnits(xData)
		yData, yPrefix = self.autosetUnits(yData)
		self.axes.set_ylabel(yPrefix + yLabel)
		self.axes.set_xlabel(xPrefix + xLabel)
		self.axes.plot(xData,yData)
		self.fig.canvas.draw()

	def autosetUnits(self, axisArray):
		"""
		Set the X units of the plot to the correct size based on the values in axisArray.

		Parameters:
			:axisArray: the array of values representing one dimension of the waveform.
		"""
		xMax = np.amax(axisArray)
		if xMax > 1e-9:
			if xMax > 1e-6:
				if xMax > 1e-3:
					if xMax > 1:
						prefix = ''
						return axisArray,prefix

					prefix = 'milli'
					axisArray = np.multiply(axisArray,1000)
					return axisArray,prefix

				prefix = 'micro'
				axisArray = np.multiply(axisArray,1e6)
				return axisArray,prefix

			prefix = 'nano'
			axisArray = np.multiply(axisArray,1e9)
			return axisArray,prefix

		prefix = ''
		return axisArray,prefix

class scopeControlWidget(QtWidgets.QWidget):
	"""
	Widget containing scope interaction widgets; buttons, selectors, etc.
	"""

	def __init__(self, scope, *args):
		"""
		Constructor.

		Parameters
			:scope: The oscilloscope to be controlled by this widget.
		"""

		self.scope = scope

		QtWidgets.QWidget.__init__(self, *args)
		self.initWidgets()
		self.show()

	def initWidgets(self):
		"""
		Set up the subwidgets
		"""
		self.acqButton = QtWidgets.QPushButton('Acquire',self)
		self.acqButton.setEnabled(False)
		self.channelComboLabel = QtWidgets.QLabel('Data Channel',self)
		self.channelComboBox = QtWidgets.QComboBox(self)
		
		if self.scope is not None:
			self.setEnabled(True)

		self.layout = QtWidgets.QGridLayout(self)
		self.layout.addWidget(self.acqButton,0,0)
		self.layout.addWidget(self.channelComboLabel,1,0)
		self.layout.addWidget(self.channelComboBox,2,0)

	def setScope(self, scope):
		"""
		Change the oscilloscope that this widget is controlling.

		Parameters:
			:scope: the new oscilloscope bject to be controlled.
		"""

		self.scope = scope
		if scope is None:
			self.setEnabled(False)
		elif scope is GenericOscilloscope:
			self.setEnabled(True)

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		self.acqButton.setEnabled(bool)
		self.channelComboBox.setEnabled(bool)
		if bool:
			channels =list(map(str,range(1,self.scope.numChannels+1)))
			self.channelComboBox.addItems(channels)

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

		QtWidgets.QApplication.__init__(self, *args)
		self.scopeControl = scopeControlWidget(None)
		self.plot = WavePlotWidget()
		self.mainWindow = scopeOutMainWindow([self.plot,self.scopeControl],self.__closeEvent,self.__saveWaveformEvent)
		self.__connectSignals()

		self.scopeThread = threading.Thread(target=self.__scopeFind)
		self.scopeThread.start()

		self.waveQueue = Queue()

	def __connectSignals(self):
		"""
		Connects signals from subwidgets to appropriate slots.
		"""

		self.scopeControl.acqButton.clicked.connect(self.__acqEvent)
		self.scopeControl.channelComboBox.currentIndexChanged.connect(self.__setChannel)

	def __acqEvent(self):
		"""
		Executed to collect waveform data from scope.
		"""

		self.acqThread = threading.Thread(target = self.__acqThread)
		self.acqThread.start()
		
	def __acqThread(self):

		if self.activeScope is not None :
			self.mainWindow.statusBar().showMessage('Acquiring data...')
			self.lock.acquire()
		
			try:
				self.activeScope.makeWaveform()
				wave = self.activeScope.getNextWaveform()
				self.waveQueue.put(self.activeScope.getNextWaveform());
			except AttributeError:
				wave = None
			finally:
				self.lock.release()

			if wave is not None and (not self.stopFlag.isSet()):
				if wave['error'] is not None:
					self.mainWindow.statusBar().showMessage(wave['error'])
				else: 
					try:
						self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'])
						self.mainWindow.statusBar().showMessage('Waveform acquired on ' +wave['dataChannel'])
					except KeyError:
						self.mainWindow.statusBar().showMessage('Waveform not complete')
			else:
				self.mainWindow.statusBar().showMessage('Error on Waveform Acquisition')

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
						self.mainWindow.statusBar().showMessage('No Oscilloscopes detected.')
						showedMessage = True
					self.lock.acquire()
					self.scopes = finder.refresh().getScopes()
					self.lock.release()

				if not self.stopFlag.isSet(): # Scope Found!
					self.activeScope = self.scopes[0]
					self.scopeControl.setScope(self.activeScope)
					self.mainWindow.statusBar().showMessage('Found ' + str(self.activeScope))
					self.mainWindow.setEnabled(True)

				while self.scopes: # See if scope is still there or if program terminates
					if self.stopFlag.isSet():
						self.scopes = []
						break
					self.lock.acquire()
					if not finder.checkScope(0):
						self.scopes = []
					self.lock.release()

				self.mainWindow.statusBar().showMessage('Connection to oscilloscope lost')
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

	def __setChannel(self,channel):
		"""
		Set data channel of active scope.

		Parameters:
			:channel: desired data channel
		"""
		def __channelThread():

			self.lock.acquire()
			if self.scopeControl.scope.setDataChannel(channel+1):
				self.mainWindow.statusBar().showMessage('Data channel set to ' + str(channel + 1))
			else:
				self.mainWindow.statusBar().showMessage('Failed to set data channel set to ' + str(channel + 1))
			self.lock.release()
			sys.exit(0)

		threading.Thread(target=__channelThread).start()

	def __saveWaveformEvent(self):
		"""
		Called in order to save in-memory waveforms to disk.
		"""
		if self.waveQueue.qsize():

			try:
				waveDirectory = os.path.join(os.getcwd(), 'waveforms')
				if not os.path.exists(waveDirectory):
					os.makedirs(waveDirectory)

				dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
				if not os.path.exists(dayDirectory):
					os.makedirs(dayDirectory)

				filename = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S')+'.csv'
				saveFile = open(os.path.join(dayDirectory,filename).replace('\\','/'),'w')
				saveFile.write('Test')
				saveFile.close()

			except Exception as e:
				print(e + 'Error on waveform saving')

		else:
			self.mainWindow.statusBar().showMessage('No Waveforms to Save')


 



