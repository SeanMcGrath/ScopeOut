"""
ScopeOut Widgets

Widget classes for Scopeout GUI.

Sean McGrath, 2014
"""

from PyQt5 import QtGui, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from lib.oscilloscopes import GenericOscilloscope
from functools import partial
import os, re, logging, numpy as np

class ScopeOutMainWindow(QtWidgets.QMainWindow):
	"""
	Class to represent entire GUI Window. Will contain various QWidgets within a QLayout,
	menu bars, tool bars, etc.
	"""

	def __init__(self, widgets, endCommand, saveCommand, *args):
		"""
		Constructor.
		will be passed widgets from threaded client (probably as array).
		"""

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.ScopeOutMainWindow')
		self.logger.info('Main Window created')

		self.widgets = widgets
		self.endCommand = endCommand
		self.saveCommand = saveCommand

		QtWidgets.QMainWindow.__init__(self, *args)

		self.central = QtWidgets.QWidget(self)
		self.layout = QtWidgets.QGridLayout(self.central)
		self.layout.addWidget(self.widgets[0],0,0)
		self.layout.addWidget(self.widgets[1],0,1)
		self.layout.addWidget(self.widgets[2],1,0)
		self.central.setLayout(self.layout)
		self.setCentralWidget(self.central)

		self.initUI()

		self.setEnabled(False)

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

        # File->Save
		saveAction = QtWidgets.QAction(QtGui.QIcon('save.png'), '&Save Waveforms', self)
		saveAction.setShortcut('Ctrl+S')
		saveAction.setStatusTip('Save Acquired Waveforms to .csv file')
		saveAction.triggered.connect(self.saveCommand)

		# Data->Reset
		self.resetAction = QtWidgets.QAction('&Reset and Clear Data', self)
		self.resetAction.setShortcut('Ctrl+R')
		self.resetAction.setStatusTip('Clear all waveforms in memory')

		# Data->Mode
		self.modeGroup = QtWidgets.QActionGroup(self)

		# Data->Mode->Wave Capture
		self.captureModeAction = QtWidgets.QAction('Wave Display', self.modeGroup)
		self.captureModeAction.setStatusTip('Display acquired waveforms')
		self.captureModeAction.setCheckable(True)
		self.captureModeAction.setChecked(True)

		# Data->Mode->Histogram
		self.histogramModeAction = QtWidgets.QAction('Histogram Display', self.modeGroup)
		self.histogramModeAction.setStatusTip('Display wave integration histogram')
		self.histogramModeAction.setCheckable(True)

        # Put title on window
		self.setWindowTitle('ScopeOut')

        # Initialize status bar at bottom of window
		self.statusBar().showMessage("Initializing")

        # Initialize "File" Section of top menu
		self.menubar = self.menuBar()
		self.fileMenu = self.menubar.addMenu('&File')
		self.fileMenu.addAction(exitAction)
		self.fileMenu.addAction(saveAction)

		# "Data" Menu
		self.dataMenu = self.menubar.addMenu('&Data')
		self.dataMenu.addAction(self.resetAction)
		acqModeMenu = self.dataMenu.addMenu('Acquisition Mode')
		acqModeMenu.addActions(self.modeGroup.findChildren(QtWidgets.QAction))

		# "View" Menu
		viewMenu = self.menubar.addMenu('&View')
		themeMenu = viewMenu.addMenu('Change Theme')
		if self.themes:
			themeActions = []
			for theme in self.themes:
				themeAction = QtWidgets.QAction(theme.split('\\')[-1].split('.')[0],self)
				themeAction.setStatusTip('Change active theme to ' + theme.split('\\')[-1].split('.')[0])
				themeAction.triggered.connect(partial(self.loadTheme,theme))
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
					self.logger.info("Loaded theme %s", self.themes[i])
					break
				else:
					i += 1

	def findThemes(self):
		"""
		Finds themes (stylesheets) in the Themes folder, currently '\lib\Themes'
		and stores their paths in self.themes.

		:Returns: self.themes, the array of theme paths, for convenience.
		"""

		path = os.path.join(os.getcwd(), 'Themes')
		self.themes = []

		try:
			themeFiles = os.listdir(path)
			for theme in themeFiles:
				if re.match('.*stylesheet',theme):
					try:
						openTheme = os.path.join(path,theme)
						self.themes.append(openTheme)
					except Exception as e:
						self.logger.info('Could not process ' + theme + ', ignoring')
		except Exception as e:
			self.logger.error(e)

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
			self.update()
		except Exception as e:
			self.logger.error(themePath + ' could not be loaded')
			return False

		return True
    
	def closeEvent(self, ev):
		"""
		Executed when window is closed or File->Exit is called.

		:ev:
			The CloseEvent in question. This is accepted by default.
		"""

		self.logger.info("Close Event accepted")
		for widget in self.widgets:
			widget.close()
		self.endCommand()
		self.close()

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		if bool:
			self.logger.info("Main Window enabled")
		else:
			self.logger.info("Main Window disabled")


		for widget in self.widgets:
			widget.setEnabled(bool)

		self.menubar.actions()[1].setEnabled(bool)
		self.menubar.actions()[0].menu().actions()[1].setEnabled(bool)

	def status(self, message):
		"""
		Slot to print message to statusbar.
		"""

		self.statusBar().showMessage(message)

class WavePlotWidget(FigureCanvas):
	"""
	Class to hold matplotlib Figures for display.
	"""

	def __init__(self):

		self.logger = logging.getLogger("ScopeOut.scopeWidgets.WavePlotWidget")
		self.fig = Figure()
		self.fig.suptitle("Waveform Capture")
		self.axes = self.fig.add_subplot(111)
		FigureCanvas.__init__(self,self.fig) 
		self.show()

	def showPlot(self, xData, xLabel, yData, yLabel, clear):
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

		:clear:
			True to draw new plot, false to add to existing plot
		'''

		if not clear: self.axes.clear()
		xData, xPrefix = self.autosetUnits(xData)
		yData, yPrefix = self.autosetUnits(yData)
		self.axes.set_ylabel(yPrefix + yLabel)
		self.axes.set_xlabel(xPrefix + xLabel)
		self.axes.plot(xData,yData)
		self.fig.canvas.draw()

	def showMultiPlot(self, xData, xLabel, yData, yLabel):
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

	def resetPlot(self):
		"""
		Reset plot to initial state.
		"""

		self.axes.clear()
		self.fig.canvas.draw()
		self.logger.info("Plot Reset")

	def vertLines(self, xArray):
		"""
		Add vertical lines at the x values in xArray.

		Parameters:
			:xArray: the list of x values at which to add vertical lines
		"""

		xArray, prefix = self.autosetUnits(xArray)
		for x in xArray:
			if x != 0:
				self.axes.axvline(x)

		self.fig.canvas.draw()

	def showHist(self, x, bins=100):
		"""
		Plot the histogram of integrated wave values.x`

		Parameters:
			:x: the histogram x data.
			:bins: the number of bins desired.
		"""

		self.fig.suptitle("Peak Histogram")
		self.axes.clear()
		self.axes.set_ylabel('Counts')
		self.axes.hist(x,bins)
		self.fig.canvas.draw()


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
		self.logger = logging.getLogger('ScopeOut.scopeWidgets.scopeControlWidget')

		self.scope = scope

		QtWidgets.QWidget.__init__(self, *args)
		self.initWidgets()
		self.show()

	def initWidgets(self):
		"""
		Set up the subwidgets
		"""
		self.acqButton = QtWidgets.QPushButton('Acquire',self)
		self.contAcqButton = QtWidgets.QPushButton('Acquire Continuously', self)
		self.autoSetButton = QtWidgets.QPushButton('Autoset',self)
		self.acqOnTrigButton = QtWidgets.QPushButton('Acquire on Trigger', self)
		self.acqStopButton = QtWidgets.QPushButton('Stop Acquisition', self)
		self.channelComboLabel = QtWidgets.QLabel('Data Channel',self)
		self.channelComboBox = QtWidgets.QComboBox(self)
		self.keepPlotCheckBox = QtWidgets.QCheckBox('Hold plot',self)
		self.keepPlotCheckBox.setChecked(True)
		
		if self.scope is not None:
			self.setEnabled(True)

		self.layout = QtWidgets.QGridLayout(self)
		self.layout.setRowMinimumHeight(1,100)
		self.layout.setRowMinimumHeight(7,100)
		self.layout.addWidget(self.autoSetButton,0,0)
		self.layout.addWidget(self.acqButton,2,0)
		self.layout.addWidget(self.acqOnTrigButton,3,0)
		self.layout.addWidget(self.contAcqButton,4,0)
		self.layout.addWidget(self.acqStopButton,5,0)
		self.layout.addWidget(self.keepPlotCheckBox,6,0)
		self.layout.addWidget(self.channelComboLabel,8,0)
		self.layout.addWidget(self.channelComboBox,9,0)
		self.setLayout(self.layout)

	def setScope(self, scope):
		"""
		Change the oscilloscope that this widget is controlling.

		Parameters:
			:scope: the new oscilloscope object to be controlled.
		"""

		self.scope = scope
		self.logger.info("Active scope set to %s", str(scope))

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
		self.autoSetButton.setEnabled(bool)
		self.channelComboBox.setEnabled(bool)
		self.acqOnTrigButton.setEnabled(bool)
		self.contAcqButton.setEnabled(bool)
		self.acqStopButton.setEnabled(bool)
		if bool and self.scope is not None:
			channels =list(map(str,range(1,self.scope.numChannels+1)))
			self.channelComboBox.addItems(channels)
			self.channelComboBox.addItem('All')
			self.channelComboBox.setCurrentIndex(0)
		else:
			self.channelComboBox.clear()

	def plotHeld(self):
		"""
		Check if 'plot hold' option is selected.
		
		:Returns: True if plot is to be held, false otherwise
		"""

		return self.keepPlotCheckBox.isChecked()

class waveOptionsWidget(QtWidgets.QWidget):
	"""
	Widget containing information and settings for captured waveforms.
	"""
	def __init__(self, *args):
		"""
		constructor.
		"""

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.waveOptionsWidget')
		QtWidgets.QWidget.__init__(self, *args)
		self.initWidgets()
		self.show()

	def initWidgets(self):
		"""
		Set up sub-widgets.
		"""

		self.waveCounter = QtWidgets.QLabel("Waveforms acquired: 0", self)
		self.showStart = QtWidgets.QCheckBox('Show Peak Window', self)
		self.startThresholdLabel = QtWidgets.QLabel("Peak Start Threshold", self)
		self.endThresholdLabel = QtWidgets.QLabel("Peak End Threshold", self)
		self.startThresholdInput = QtWidgets.QSpinBox(self)
		self.startThresholdInput.setMaximum(500)
		self.startThresholdInput.setMinimum(0)
		self.startThresholdInput.setSuffix('%')
		self.startThresholdInput.setValue(10)
		self.endThresholdInput = QtWidgets.QDoubleSpinBox(self)
		self.endThresholdInput.setMaximum(500.0)
		self.endThresholdInput.setMinimum(0.0)
		self.endThresholdInput.setSuffix('%')
		self.endThresholdInput.setValue(100)

		self.layout = QtWidgets.QGridLayout(self)
		self.layout.addWidget(self.waveCounter,0,0)
		self.layout.addWidget(self.showStart,0,1)
		self.layout.addWidget(self.startThresholdLabel,0,2)
		self.layout.addWidget(self.startThresholdInput,0,3)
		self.layout.addWidget(self.endThresholdLabel,1,2)
		self.layout.addWidget(self.endThresholdInput,1,3)
		self.setLayout(self.layout)

	def updateCount(self, waves):
		"""
		Updates the displayed count of acquired waves.

		Parameters:
			:waves: the integer number of acquired waves.
		"""

		self.waveCounter.setText("Waveforms acquired: " + str(waves))

	def getThresholds(self):
		"""
		Returns the peak thresholds as decimals.

		:Returns: An array containting the start threshold followed by the end threshold.
		"""

		return [self.startThresholdInput.value()/100.0, self.endThresholdInput.value()/100.0]

	def peakStart(self):
		"""
		Returns checked value of "show peak start" box.
		"""

		return self.showStart.isChecked()

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		self.startThresholdInput.setEnabled(bool)
		self.endThresholdInput.setEnabled(bool)

