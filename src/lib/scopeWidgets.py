"""
ScopeOut Widgets

Widget classes for Scopeout GUI.

Sean McGrath, 2014
"""

from PyQt5 import QtGui, QtWidgets, QtCore
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
		self.layout.setSpacing(0)
		self.layout.setContentsMargins(0,0,0,0)
		self.layout.addWidget(self.widgets[0],0,0)
		self.layout.addWidget(self.widgets[1],0,1)
		self.layout.addWidget(self.widgets[2],2,0)
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
		self.fig.suptitle("Waveform Capture", color='white')
		self.fig.patch.set_color('#3C3C3C')
		self.axes = self.fig.add_subplot(111)
		[t.set_color('white') for t in self.axes.yaxis.get_ticklabels()]
		[t.set_color('white') for t in self.axes.xaxis.get_ticklabels()]
		self.axes.xaxis.label.set_color('white')
		self.axes.yaxis.label.set_color('white')
		FigureCanvas.__init__(self,self.fig)
		self.setContentsMargins(5,5,5,5)
		self.show()

	def showPlot(self, xData, xLabel, yData, yLabel, hold):
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

		:hold:
			True to hold existing plot, false to make new plot
		'''

		if not hold: self.resetPlot()
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
		self.fig.patch.set_color('#3C3C3C')
		self.axes = self.fig.add_subplot(111)
		[t.set_color('white') for t in self.axes.yaxis.get_ticklabels()]
		[t.set_color('white') for t in self.axes.xaxis.get_ticklabels()]
		self.axes.xaxis.label.set_color('white')
		self.axes.yaxis.label.set_color('white')
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

class acqControlWidget(QtWidgets.QWidget):
	"""
	Widget containing acquisition control objects.
	"""

	def __init__(self, scope, *args):
		"""
		Constructor.

		Parameters
			:scope: The oscilloscope to be controlled by this widget.
		"""
		self.logger = logging.getLogger('ScopeOut.scopeWidgets.acqControlWidget')

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
			channels.append('All')
			channels.append('Math')
			self.channelComboBox.addItems(channels)
			self.channelComboBox.setCurrentIndex(0)
		else:
			self.channelComboBox.clear()

	def plotHeld(self):
		"""
		Check if 'plot hold' option is selected.
		
		:Returns: True if plot is to be held, false otherwise
		"""

		return self.keepPlotCheckBox.isChecked()

	def getChannels(self):
		"""
		Returns a list of the available data channels.
		"""

		return [self.channelComboBox.itemText(i) for i in range(self.channelComboBox.count())]

class SmartPeakTab(QtWidgets.QWidget):
	"""
	Widget controlling smart peak detection algorithm.
	"""

	def __init__(self, *args):
		"""
		constructor.
		"""

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.SmartPeakTab')
		QtWidgets.QWidget.__init__(self, *args)
		self.initWidgets()
		self.show()

	def initWidgets(self):
		"""
		Set up sub-widgets.
		"""

		
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

		self.layout.addWidget(self.startThresholdLabel,0,0)
		self.layout.addWidget(self.startThresholdInput,0,1)
		self.layout.addWidget(self.endThresholdLabel,1,0)
		self.layout.addWidget(self.endThresholdInput,1,1)
		self.setLayout(self.layout)

	def getParameters(self):
		"""
		Returns the peak thresholds as decimals.

		:Returns: An array containting the start threshold followed by the end threshold.
		"""

		return [self.startThresholdInput.value()/100.0, self.endThresholdInput.value()/100.0]

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		self.startThresholdInput.setEnabled(bool)
		self.endThresholdInput.setEnabled(bool)

class FixedPeakTab(QtWidgets.QWidget):
	"""
	Widget controlling smart peak detection algorithm.
	"""

	units = {'S': 1, 'mS': 1e-3, 'uS': 1e-6, 'nS': 1e-9}

	def __init__(self, *args):
		"""
		constructor.
		"""

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.FixedPeakTab')
		QtWidgets.QWidget.__init__(self, *args)
		self.initWidgets()
		self.show()

	def initWidgets(self):
		"""
		Set up sub-widgets.
		"""
		
		self.startTimeLabel = QtWidgets.QLabel("Peak Start Time", self)
		self.peakWidthLabel = QtWidgets.QLabel("Peak Width", self)
		self.startTimeInput = QtWidgets.QDoubleSpinBox(self)
		self.startTimeInput.setMaximum(500)
		self.startTimeInput.setMinimum(0)
		self.startTimeInput.setValue(10)
		self.startTimeUnits = QtWidgets.QComboBox(self)
		self.startTimeUnits.addItems(self.units.keys())
		self.peakWidthInput = QtWidgets.QDoubleSpinBox(self)
		self.peakWidthInput.setMinimum(0)
		self.peakWidthInput.setValue(10)
		self.peakWidthUnits = QtWidgets.QComboBox(self)
		self.peakWidthUnits.addItems(self.units.keys())

		self.layout = QtWidgets.QGridLayout(self)

		self.layout.addWidget(self.startTimeLabel,0,0)
		self.layout.addWidget(self.startTimeInput,0,1)
		self.layout.addWidget(self.startTimeUnits,0,2)
		self.layout.addWidget(self.peakWidthLabel,1,0)
		self.layout.addWidget(self.peakWidthInput,1,1)
		self.layout.addWidget(self.peakWidthUnits,1,2)
		self.setLayout(self.layout)

	def getParameters(self):
		"""
		Returns the peak thresholds as decimals.

		:Returns: An array containing the peak start time and the peak width in seconds
		"""

		return [self.startTimeInput.value()*self.units[self.startTimeUnits.currentText()], self.peakWidthInput.value()*self.units[self.peakWidthUnits.currentText()]]

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		self.startThresholdInput.setEnabled(bool)
		self.endThresholdInput.setEnabled(bool)


class waveOptionsTabWidget(QtWidgets.QWidget):
	"""
	Manages Tabbed display of wave options widgets. Also holds wave counter and peak window checkbox
	"""

	def __init__(self, *args):
		"""
		Constructor
		"""

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.waveOptionsTabWidget')
		QtWidgets.QWidget.__init__(self, *args)

		self.waveCounter = QtWidgets.QLabel("Waveforms acquired: 0", self)
		self.showWindow = QtWidgets.QCheckBox('Show Peak Window', self)

		self.tabManager = QtWidgets.QTabWidget(self)
		self.smart = SmartPeakTab(None)
		self.fixed = FixedPeakTab(None)

		self.tabTitles = ['Smart', 'Fixed']
		self.tabManager.addTab(self.smart, self.tabTitles[0])
		self.tabManager.addTab(self.fixed,self.tabTitles[1])

		self.layout = QtWidgets.QGridLayout(self)

		self.layout.addWidget(self.waveCounter,0,0)
		self.layout.addWidget(self.showWindow,1,0)
		self.layout.addWidget(self.tabManager,0,1,2,1)
		self.show()

	def updateCount(self, waves):
		"""
		Updates the displayed count of acquired waves.

		Parameters:
			:waves: the integer number of acquired waves.
		"""

		self.waveCounter.setText("Waveforms acquired: " + str(waves))

	def peakStart(self):
		"""
		Returns checked value of "show peak start" box.
		"""

		return self.showWindow.isChecked()

	def currentWidget(self):
		"""
		Get currently displayed tab
		"""

		return self.tabManager.currentWidget()

	def getParameters(self):
		"""
		Fetch the relevant peak-detection parameters from the current tab
		"""

		return self.currentWidget().getParameters()

	def getMode(self):
		"""
		Fetch a string indicating the current peak detection mode
		"""

		return self.tabTitles[self.tabManager.currentIndex()]