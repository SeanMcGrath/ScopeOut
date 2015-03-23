"""
ScopeOut Widgets

Widget classes for Scopeout GUI.

Sean McGrath, 2014
"""

from PyQt5 import QtGui, QtWidgets, QtCore
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from lib.oscilloscopes import GenericOscilloscope
from functools import partial
from collections import OrderedDict
import os, re, logging, numpy as np, seaborn as sns

# Graph configuration
sns.set(font_scale=1.25)
sns.set_palette(["#673AB7", "#3498db", "#95a5a6", "#e74c3c", "#34495e", "#2ecc71"])

class ScopeOutWidget(QtWidgets.QWidget):
	"""
	Base class for the QWidgets that make up the ScopeOut interface.
	Provides methods important to the consistent styling of the application.
	"""

	units = OrderedDict([('nS', 1e-9),('uS', 1e-6),('mS', 1e-3),('S', 1)])

	def __init__(self, *args):

		QtWidgets.QWidget.__init__(self, *args)

		# Just add actions to the widget to get right click menus
		self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

	def addShadow(self, widget=None):
		"""
		Add a uniform drop shadow to the calling widget or the target widget.

		Parameters:
			:widget: a QWidget which will receive the drop shadow. If no argument is passed, the
					 shadow will be applied to the calling widget.
		"""

		if widget:
			shadow = QtWidgets.QGraphicsDropShadowEffect(widget)
			shadow.setBlurRadius(8)
			shadow.setXOffset(1)
			shadow.setYOffset(2)
			shadow.setColor(QtGui.QColor('black'))
			widget.setGraphicsEffect(shadow)

		else:
			shadow = QtWidgets.QGraphicsDropShadowEffect(self)
			shadow.setBlurRadius(8)
			shadow.setXOffset(1)
			shadow.setYOffset(2)
			shadow.setColor(QtGui.QColor('black'))
			self.setGraphicsEffect(shadow)

	def paintEvent(self, pe):
		"""
		Enables the use of a global stylesheet.
		"""
		
		opt = QtWidgets.QStyleOption()
		opt.initFrom(self)
		p = QtGui.QPainter(self)
		s = self.style()
		s.drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, p, self)

class ScopeOutScrollArea(QtWidgets.QScrollArea):

	def __init__(self, *args):

		QtWidgets.QScrollArea.__init__(self, *args)

	def addShadow(self, widget=None):
		"""
		Add a uniform drop shadow to the calling widget or the target widget.

		Parameters:
			:widget: a QWidget which will receive the drop shadow. If no argument is passed, the
					 shadow will be applied to the calling widget.
		"""

		if widget:
			shadow = QtWidgets.QGraphicsDropShadowEffect(widget)
			shadow.setBlurRadius(8)
			shadow.setXOffset(1)
			shadow.setYOffset(2)
			shadow.setColor(QtGui.QColor('black'))
			widget.setGraphicsEffect(shadow)

		else:
			shadow = QtWidgets.QGraphicsDropShadowEffect(self)
			shadow.setBlurRadius(8)
			shadow.setXOffset(1)
			shadow.setYOffset(2)
			shadow.setColor(QtGui.QColor('black'))
			self.setGraphicsEffect(shadow)

class ScopeOutPlotWidget(FigureCanvas):
	"""
	Base class for matplotlib figure widgets.
	"""
	bgColor = '#424242'

	def __init__(self):
		"""
		Constructor

		Parameters:
			:figure: a matplotlib figure to be displayed.
		"""

		self.logger = logging.getLogger("ScopeOut.scopeWidgets.ScopeOutPlotWidget")
		self.fig = Figure()
		FigureCanvas.__init__(self,self.fig)

		self.setContentsMargins(5,5,5,5)
		
		self.fig.patch.set_color(self.bgColor)
		self.axes = self.fig.add_subplot(111)
		self.axes.xaxis.label.set_color('white')
		self.axes.yaxis.label.set_color('white')
		self.coords = self.axes.text(0,0,'')
		[t.set_color('white') for t in self.axes.yaxis.get_ticklabels()]
		[t.set_color('white') for t in self.axes.xaxis.get_ticklabels()]

	def displayCoords(self, event):
		"""
		display the coordinates of the mouse on the graph.

		Parameters:
			:event: an event object containing the mouse location data.
		"""

		if event.inaxes:
			eventString = 'x: {} {}   y: {} {}'.format(
				round(event.xdata,5), self.axes.get_xlabel(), round(event.ydata, 5), self.axes.get_ylabel())
			self.coords.remove()
			self.coords = self.axes.text(0.05, 0.95,eventString, ha='left', va='center', transform=self.axes.transAxes)
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
		self.axes = self.fig.add_subplot(111)
		[t.set_color('white') for t in self.axes.yaxis.get_ticklabels()]
		[t.set_color('white') for t in self.axes.xaxis.get_ticklabels()]
		self.coords = self.axes.text(0,0,'')
		self.logger.info("Plot Reset")

	def savePlot(self, filename):
		"""
		Save the figure to disk.

		Parameters:
			:filename: a string giving the desired save file name.

		:Returns: True if save successful, false otherwise.
		"""

		try:
			self.fig.savefig(filename, bbox_inches='tight', facecolor='#3C3C3C')
			return True
		except Exception as e:
			self.logger.error(e)
			return False

class ScopeOutMainWindow(QtWidgets.QMainWindow):
	"""
	Class to represent entire GUI Window. Manages the subwidgets that make up the interface,
	Including custom ScopeOut widgets as well as the statusbar, menubar, etc.
	"""

	def __init__(self, widgets, commands, *args):
		"""
		Constructor.
		Is passed widgets from threaded client as an array.

		Parameters:
			:widgets: the array containing the child widgets to be displayed by this window.
			:commands: a dictionary of commands to be executed when various actions of the window are invoked.
		"""

		QtWidgets.QMainWindow.__init__(self, *args)

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.ScopeOutMainWindow')
		self.logger.info('Main Window created')

		self.widgets = widgets

		self.endCommand = commands['end']

		self.central = QtWidgets.QWidget(self)
		self.layout = QtWidgets.QGridLayout(self.central)

		self.layout.setSpacing(20)
		self.layout.setContentsMargins(0,0,0,0)
		self.layout.addWidget(self.widgets['column'],0,0,4,1) # Column
		self.layout.addWidget(self.widgets['plot'],1,2,1,1) # plot
		self.widgets['plot'].show()
		self.layout.addWidget(self.widgets['acqControl'],0,4,4,1) # acqControl
		self.layout.addWidget(self.widgets['options'],2,2) # waveOptions
		self.layout.setColumnMinimumWidth(4,180)
		self.layout.setColumnMinimumWidth(2,600)
		self.layout.setColumnStretch(0,1)
		self.layout.setColumnStretch(2,1)
		self.layout.setRowStretch(0,1)
		self.layout.setRowStretch(1,1)
		self.layout.setRowStretch(3,1)
		self.layout.setRowMinimumHeight(3,20)
		self.layout.setRowMinimumHeight(1,500)
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
		self.saveAction = QtWidgets.QAction(QtGui.QIcon('save.png'), '&Save Waveforms', self)
		self.saveAction.setShortcut('Ctrl+S')
		self.saveAction.setStatusTip('Save All Acquired Waveforms to .csv file')

		# File-> Save Properties
		self.savePropertiesAction = QtWidgets.QAction(QtGui.QIcon('save.png'), 'Save Waveform Properties', self)
		self.savePropertiesAction.setShortcut('Ctrl+Alt+S')
		self.savePropertiesAction.setStatusTip('Save desired properties of waveforms to .csv file')

		# File-> Save Plot
		self.savePlotAction = QtWidgets.QAction(QtGui.QIcon('save.png'), 'Save Plot', self)
		self.savePlotAction.setStatusTip('Save plot image to disk.')

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
		self.histogramModeAction.toggled.connect(self.plotSelect)

        # Put title on window
		self.setWindowTitle('ScopeOut')

        # Initialize status bar at bottom of window
		self.statusBar().showMessage("Initializing")

        # Initialize "File" Section of top menu
		self.menubar = self.menuBar()
		self.fileMenu = self.menubar.addMenu('&File')
		self.fileMenu.addAction(exitAction)
		self.fileMenu.addAction(self.saveAction)
		self.fileMenu.addAction(self.savePropertiesAction)
		self.fileMenu.addAction(self.savePlotAction)

		# "Data" Menu
		self.dataMenu = self.menubar.addMenu('&Data')
		self.dataMenu.addAction(self.resetAction)
		acqModeMenu = self.dataMenu.addMenu('Acquisition Mode')
		acqModeMenu.addActions(self.modeGroup.findChildren(QtWidgets.QAction))

		# "View" Menu
		viewMenu = self.menubar.addMenu('&View')
		themeMenu = viewMenu.addMenu('Change Theme')
		if self.themes:
			for theme in self.themes:
				themeAction = QtWidgets.QAction(theme.split('\\')[-1].split('.')[0],self)
				themeAction.setStatusTip('Change active theme to ' + theme.split('\\')[-1].split('.')[0])
				themeAction.triggered.connect(partial(self.loadTheme,theme))
				themeMenu.addAction(themeAction)
		else:
			themeMenu.setEnabled(False)

	def initTheme(self):
		"""
		Finds all themes, and loads first available one.
		"""

		def findThemes():
			"""
			Finds themes (stylesheets) in the Themes folder, currently '\lib\Themes'
			and stores their paths in self.themes.

			:Returns: themes, the array of theme paths, for convenience.
			"""

			path = os.path.join(os.getcwd(), 'Themes')
			themes = []

			try:
				themeFiles = os.listdir(path)
				themes = [os.path.join(path,theme) for theme in themeFiles if re.match('.*stylesheet',theme)]
			except Exception as e:
				self.logger.error(e)

			return themes

		self.themes = findThemes()
		if self.themes:
			i = 0
			while True:
				if i > len(self.themes) - 1:
					break
				elif self.loadTheme(self.themes[i]):
					self.logger.info("Loaded theme %s", self.themes[i])
					break
				else:
					i += 1

	def loadTheme(self, themePath):
		"""
		Loads style sheet from themePath and sets it as the application's style.

		Parameters:
			:themePath: the absolute path to a styesheet defining a theme.

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
			self.widgets[widget].close()
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
			self.widgets[widget].setEnabled(bool)

		self.menubar.actions()[1].setEnabled(bool)
		self.menubar.actions()[0].menu().actions()[1].setEnabled(bool)
		self.menubar.actions()[0].menu().actions()[2].setEnabled(bool)

	def status(self, message):
		"""
		Slot to print message to statusbar.

		Parameters:
			:message: The string to be displayed.
		"""

		self.statusBar().showMessage(message)

	def plotSelect(self, bool):
		"""
		Switch between display of histogram and wave plots.

		Parameters:
			:bool: true to display histogram, false for wave plot.
		"""

		if bool:
			self.widgets['plot'].hide()
			self.layout.replaceWidget(self.widgets['plot'],self.widgets['hist'])
			self.widgets['hist'].show()
			
		else:
			self.widgets['hist'].hide()
			self.layout.replaceWidget(self.widgets['hist'],self.widgets['plot'])
			self.widgets['plot'].show()

class WavePlotWidget(ScopeOutPlotWidget):
	"""
	Class to hold matplotlib Figures for display.
	"""

	def __init__(self):
		"""
		Constructor
		"""

		ScopeOutPlotWidget.__init__(self)
		self.logger = logging.getLogger("ScopeOut.scopeWidgets.WavePlotWidget")
		self.fig.suptitle("Waveform Capture", color='white')
		self.logger.info("Wave Plot initialized")

	def showPlot(self, wave, hold=False, showPeak=False):
		'''
		Fill plot with data and draw it on the screen.

		:wave:
			a wave dictionary object

		:hold:
			True to add to existing plot, false to make new plot
		'''

		if not hold: self.resetPlot()
		self.fig.suptitle("Waveform Capture", color='white')
		xData, xPrefix = self.autosetUnits(wave['xData'])
		yData, yPrefix = self.autosetUnits(wave['yData'])
		self.axes.set_ylabel(yPrefix + wave['Y Unit'])
		self.axes.set_xlabel(xPrefix + wave['X Unit'])
		self.axes.plot(xData,yData)
		if showPeak:
			self.vertLines([ wave['xData'][wave['Start of Peak']], wave['xData'][wave['End of Peak']] ])
		cursor = Cursor(self.axes, useblit=True, color='black', linewidth=1 )
		cursor.connect_event('motion_notify_event', self.displayCoords)
		self.fig.canvas.draw()

	def vertLines(self, xArray):
		"""
		Add vertical lines at the x values in xArray.

		Parameters:
			:xArray: the list of x values at which to add vertical lines
		"""

		xArray, prefix = self.autosetUnits(xArray)
		for x in xArray:
			if x >= 0:
				self.axes.axvline(x)

		self.logger.info("drew vertical lines")

class HistogramPlotWidget(ScopeOutPlotWidget):
	"""
	Widget holding a matplotlib histogram.
	"""

	def __init__(self):
		"""
		Constructor
		"""

		ScopeOutPlotWidget.__init__(self)
		self.logger = logging.getLogger("ScopeOut.scopeWidgets.HistogramPlotWidget")
		self.fig.suptitle("Peak Histogram", color='white')
		self.logger.info("Histogram Plot initialized")

	def showHist(self, x, bins=100):
		"""
		Plot the histogram of integrated wave values.

		Parameters:
			:x: the histogram x data.
			:bins: the number of bins desired.
		"""

		self.resetPlot()
		self.fig.suptitle("Peak Histogram", color='white')
		self.axes.set_ylabel('Counts')
		self.axes.hist(x,bins)
		self.fig.canvas.draw()

class acqControlWidget(ScopeOutWidget):
	"""
	Widget containing acquisition control objects.
	"""

	def __init__(self, scope, *args):
		"""
		Constructor.

		Parameters
			:scope: The oscilloscope to be controlled by this widget.
		"""

		ScopeOutWidget.__init__(self, *args)
		self.logger = logging.getLogger('ScopeOut.scopeWidgets.acqControlWidget')

		self.scope = scope

		self.initWidgets()
		self.addShadow()
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
		self.holdPlotCheckBox = QtWidgets.QCheckBox('Hold plot',self)
		self.channelComboLabel = QtWidgets.QLabel('Data Channel',self)
		self.channelComboBox = QtWidgets.QComboBox(self)
		self.holdPlotCheckBox.setChecked(False)

		if self.scope is not None:
			self.setEnabled(True)

		self.layout = QtWidgets.QGridLayout(self)
		self.layout.setRowStretch(0,1)
		self.layout.setRowMinimumHeight(2,100)
		self.layout.setRowStretch(2,1)
		self.layout.setRowMinimumHeight(8,100)
		self.layout.setRowStretch(8,1)
		self.layout.addWidget(self.autoSetButton,1,0)
		self.layout.addWidget(self.acqButton,3,0)
		self.layout.addWidget(self.acqOnTrigButton,4,0)
		self.layout.addWidget(self.contAcqButton,5,0)
		self.layout.addWidget(self.acqStopButton,6,0)
		self.layout.addWidget(self.holdPlotCheckBox,7,0)
		self.layout.addWidget(self.channelComboLabel,9,0)
		self.layout.addWidget(self.channelComboBox,10,0)
		self.layout.setRowStretch(11,1)
		self.setLayout(self.layout)

		for i in range(0,self.layout.count()):
			self.addShadow(self.layout.itemAt(i).widget())
		

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
		elif bool: # Wait for scope to become active
			while self.scope is None:
				pass
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

		return self.holdPlotCheckBox.isChecked()

	def getChannels(self):
		"""
		Returns a list of the available data channels.
		"""

		return [self.channelComboBox.itemText(i) for i in range(self.channelComboBox.count())]

class waveOptionsTabWidget(ScopeOutWidget):
	"""
	Manages Tabbed display of wave options widgets. Also holds wave counter and peak window checkbox
	"""

	class SmartPeakTab(ScopeOutWidget):
		"""
		Widget controlling smart peak detection algorithm.
		"""

		def __init__(self, *args):
			"""
			constructor.
			"""

			self.logger = logging.getLogger('ScopeOut.scopeWidgets.SmartPeakTab')
			ScopeOutWidget.__init__(self, *args)
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

			for i in range(0,self.layout.count()):
				self.addShadow(self.layout.itemAt(i).widget())

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

	class FixedPeakTab(ScopeOutWidget):
		"""
		Widget controlling Fixed-width peak detection algorithm.
		"""

		def __init__(self, *args):
			"""
			constructor.
			"""

			self.logger = logging.getLogger('ScopeOut.scopeWidgets.FixedPeakTab')
			ScopeOutWidget.__init__(self, *args)
			self.initWidgets()
			self.show()

		def initWidgets(self):
			"""
			Set up sub-widgets.
			"""
			
			self.startTimeLabel = QtWidgets.QLabel("Peak Start Time", self)
			self.peakWidthLabel = QtWidgets.QLabel("Peak Width", self)
			self.startTimeInput = QtWidgets.QDoubleSpinBox(self)
			self.startTimeInput.setMaximum(1000)
			self.startTimeInput.setMinimum(0)
			self.startTimeInput.setValue(10)
			self.startTimeUnits = QtWidgets.QComboBox(self)
			self.startTimeUnits.addItems(self.units.keys())
			self.peakWidthInput = QtWidgets.QDoubleSpinBox(self)
			self.peakWidthInput.setMaximum(1000)
			self.peakWidthInput.setMinimum(0)
			self.peakWidthInput.setValue(10)
			self.peakWidthUnits = QtWidgets.QComboBox(self)
			self.peakWidthUnits.addItems(self.units.keys())

			self.layout = QtWidgets.QGridLayout(self)
			self.layout.setContentsMargins(20,5,20,5)
			self.layout.setHorizontalSpacing(20)

			self.layout.addWidget(self.startTimeLabel,0,0)
			self.layout.addWidget(self.startTimeInput,0,1)
			self.layout.addWidget(self.startTimeUnits,0,2)
			self.layout.addWidget(self.peakWidthLabel,1,0)
			self.layout.addWidget(self.peakWidthInput,1,1)
			self.layout.addWidget(self.peakWidthUnits,1,2)
			self.setLayout(self.layout)

			for i in range(0,self.layout.count()):
				self.addShadow(self.layout.itemAt(i).widget())

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

	class HybridPeakTab(ScopeOutWidget):
		"""
		Widget controlling hybrid peak detection algorithm.
		"""

		def __init__(self, *args):
			"""
			constructor.
			"""

			self.logger = logging.getLogger('ScopeOut.scopeWidgets.HybridPeakTab')
			ScopeOutWidget.__init__(self, *args)
			self.initWidgets()
			self.show()

		def initWidgets(self):
			"""
			Set up sub-widgets.
			"""
			
			self.startThresholdLabel = QtWidgets.QLabel("Peak Start Threshold", self)
			self.peakWidthLabel = QtWidgets.QLabel("Peak Width", self)
			self.startThresholdInput = QtWidgets.QSpinBox(self)
			self.startThresholdInput.setMaximum(500)
			self.startThresholdInput.setMinimum(0)
			self.startThresholdInput.setSuffix('%')
			self.startThresholdInput.setValue(10)
			self.peakWidthInput = QtWidgets.QDoubleSpinBox(self)
			self.peakWidthInput.setMaximum(1000)
			self.peakWidthInput.setMinimum(0)
			self.peakWidthInput.setValue(10)
			self.peakWidthUnits = QtWidgets.QComboBox(self)
			self.peakWidthUnits.addItems(self.units.keys())

			self.layout = QtWidgets.QGridLayout(self)
			self.layout.setContentsMargins(20,5,20,5)
			self.layout.setHorizontalSpacing(20)

			self.layout.addWidget(self.startThresholdLabel,0,0)
			self.layout.addWidget(self.startThresholdInput,0,1)
			self.layout.addWidget(self.peakWidthLabel,1,0)
			self.layout.addWidget(self.peakWidthInput,1,1)
			self.layout.addWidget(self.peakWidthUnits,1,2)
			self.setLayout(self.layout)

			for i in range(0,self.layout.count()):
				self.addShadow(self.layout.itemAt(i).widget())

		def getParameters(self):
			"""
			Returns the peak thresholds as decimals.

			:Returns: An array containing the peak start time and the peak width in seconds
			"""

			return [self.startThresholdInput.value()/100.0, self.peakWidthInput.value()*self.units[self.peakWidthUnits.currentText()]]

		def setEnabled(self, bool):
			"""
			Enable/disable this widget.

			Parameters:
				:bool: True to enable, false to disable.
			"""

			self.startThresholdInput.setEnabled(bool)
			self.endThresholdInput.setEnabled(bool)

	def __init__(self, *args):
		"""
		Constructor
		"""

		self.logger = logging.getLogger('ScopeOut.scopeWidgets.waveOptionsTabWidget')
		ScopeOutWidget.__init__(self, *args)

		self.waveCounter = QtWidgets.QLabel("Waveforms acquired: 0", self)
		self.showWindow = QtWidgets.QCheckBox('Show Peak Window', self)
		self.addShadow(self.waveCounter)
		self.addShadow(self.showWindow)

		self.tabManager = QtWidgets.QTabWidget(self)
		self.smart = self.SmartPeakTab(None)
		self.fixed = self.FixedPeakTab(None)
		self.hybrid = self.HybridPeakTab(None)

		self.tabTitles = ['Smart Peak Detection', 'Fixed Width Peak Detection', 'Hybrid Peak Detection']
		self.tabManager.addTab(self.smart, self.tabTitles[0])
		self.tabManager.addTab(self.fixed, self.tabTitles[1])
		self.tabManager.addTab(self.hybrid, self.tabTitles[2])

		self.layout = QtWidgets.QGridLayout(self)

		self.layout.addWidget(self.waveCounter,1,1)
		self.layout.addWidget(self.showWindow,2,1)
		self.layout.addWidget(self.tabManager,0,2,4,1)
		self.layout.setRowMinimumHeight(0,30)
		self.layout.setRowStretch(4,1)
		self.layout.setVerticalSpacing(0)
		self.layout.setHorizontalSpacing(15)
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
		:Returns: the boolean value of "show peak start" checkbox.
		"""

		return self.showWindow.isChecked()

	def currentWidget(self):
		"""
		:Returns: a widget object representing the currently displayed tab
		"""

		return self.tabManager.currentWidget()

	def getParameters(self):
		"""
		:Returns: the relevant peak-detection parameters from the current tab
		"""

		return self.currentWidget().getParameters()

	def getMode(self):
		"""
		:Returns: a string indicating the current peak detection mode
		"""

		return self.tabTitles[self.tabManager.currentIndex()]

class waveColumnWidget(ScopeOutScrollArea):
	"""
	A column display showing acquired waveforms.
	"""

	waveSignal = QtCore.pyqtSignal(dict) # signal to pass wave to plot
	saveSignal = QtCore.pyqtSignal(dict) # signal to pass wave to saving routine
	savePropsSignal = QtCore.pyqtSignal(dict) # signal to pass wave to property saving routine

	class waveColumnItem(ScopeOutWidget):
		"""
		A rectangular box showing basic information about a captured waveform.
		Used to dynamically populate the waveColumnWidget.
		"""

		waveSignal = QtCore.pyqtSignal(dict)
		saveSignal = QtCore.pyqtSignal(dict)
		savePropsSignal = QtCore.pyqtSignal(dict) # signal to pass wave to property saving routine

		def __init__(self, wave, index, *args):
			"""
			constructor

			Parameters:
				:wave: the wave dictionary to be wrapped.
				:index: the index of the wave in the waveColumnWidget.
			"""

			ScopeOutWidget.__init__(self, *args)

			self.logger = logging.getLogger('ScopeOut.scopeWidgets.waveColumnItem')

			# Actions	
			dispAction = QtWidgets.QAction('Display Waveform', self)
			dispAction.triggered.connect(self.dispWave)
			self.addAction(dispAction)

			self.properties = None
			propsAction = QtWidgets.QAction('Display Properties', self)
			propsAction.triggered.connect(self.makePopup)
			self.addAction(propsAction)

			self.saveAction = QtWidgets.QAction('Save Waveform',self)
			self.saveAction.triggered.connect(lambda: self.saveSignal.emit(self.getWave()))
			self.addAction(self.saveAction)

			savePropsAction = QtWidgets.QAction('Save Properties', self)
			savePropsAction.triggered.connect(lambda: self.savePropsSignal.emit(self.getWave()))
			self.addAction(savePropsAction)

			# Setup Widgets
			self.wave = wave
			time = wave['Acquisition Time']
			dispTime = self.makeDispTime(time)
			self.waveTime = QtWidgets.QLabel('Time: ' + dispTime, self)
			self.waveNumber = QtWidgets.QLabel(str(index), self)

			# Layout
			self.layout = QtWidgets.QGridLayout(self)
			self.layout.setContentsMargins(0,0,0,0)
			self.layout.setSpacing(2)
			self.layout.addWidget(self.waveNumber,0,0)
			self.layout.addWidget(self.waveTime,0,1)
			if self.peakDetected():
				self.layout.addWidget(QtWidgets.QLabel('^',self),0,2)
				self.layout.setColumnStretch(3,1)
			else:
				self.layout.setColumnStretch(2,1)
			self.setLayout(self.layout)

		def makeDispTime(self, datetime):
			"""
			Converts the time of wave acquisiton into a tidier format for display.
			
			Parameters:
				:datetime: acquisition time string generated by DateTime
			"""

			time, partial = datetime.split(' ')[-1].split('.')
			return '{}.{}'.format(time,partial[:2])

		def getWave(self):
			"""
			:Returns: the wave wrapped by this item.
			"""

			return self.wave

		def mousePressEvent(self, event):
			"""
			Emits waveSignal on widget click, which should result in the wrapped wave being plotted.
			"""

			if event.button() == QtCore.Qt.LeftButton:
				self.dispWave()

		def dispWave(self):
			"""
			Causes the wave to be displayed and updates the column to make this item active.
			"""

			self.waveSignal.emit(self.wave)
			self.setProperty('state','active')
			self.style().unpolish(self)
			self.style().polish(self)
			self.update()

		def makePopup(self):
			"""
			Spawns properties popup window when activated.
			Makes new window if no cached version exists.
			"""

			if self.properties is None:
				self.properties = self.PropertiesPopup(self.wave)
				self.properties.setGeometry(QtCore.QRect(100, 100, 400, 200))

			self.properties.show()

		def peakDetected(self):
			"""
			Returns true if the wrapped peak has a detected wave, False otherwise
			"""
			try:
				return self.wave['Start of Peak'] > 0
			except KeyError:
				return False

		class PropertiesPopup(ScopeOutWidget):
			"""
			Popup window to display wave properties.
			"""

			def __init__(self, wave, *args):
				"""
				Constructor.

				Parameters:
					:wave: The wave dictionary whose properties are to be displayed.
				"""

				ScopeOutWidget.__init__(self, *args)
				self.logger = logging.getLogger('ScopeOut.scopeWidgets.waveColumnItem.PropertiesPopup')

				self.setWindowTitle('Wave Properties')
				self.setStyleSheet('color: white; background-color: #3C3C3C;')

				layout = QtWidgets.QGridLayout(self)
				layout.addWidget(QtWidgets.QLabel('Wave Properties:',self),0,0)

				# Add base property readouts
				y = 1
				for field in sorted(wave.keys()):
					if not isinstance(wave[field], list) and field.lower() not in ['xdata','ydata']:
						label = QtWidgets.QLabel('  '+field, self)
						layout.addWidget(label,y,0)
						value = QtWidgets.QLabel('{}'.format(wave[field]),self)
						layout.addWidget(value,y,1)
						y += 1

				# Added peak properties section
				layout.setRowMinimumHeight(y+1,10)
				layout.addWidget(QtWidgets.QLabel('Peak Properties:',self),y+2,0)
				if wave['Start of Peak'] < 0:
					layout.addWidget(QtWidgets.QLabel('  No Peak Detected',self),y+3,0)
				else:
					startString = str(wave['xData'][wave['Start of Peak']]) + ' ' + str(wave['X Unit'])
					endString = str(wave['xData'][wave['End of Peak']]) + ' ' +  str(wave['X Unit'])
					widthString = "{} {}".format(wave['xData'][wave['End of Peak']] - wave['xData'][wave['Start of Peak']], wave['X Unit'])
					layout.addWidget(QtWidgets.QLabel('  Peak Start',self),y+3,0)
					layout.addWidget(QtWidgets.QLabel(startString,self),y+3,1)
					layout.addWidget(QtWidgets.QLabel('  Peak End',self),y+4,0)
					layout.addWidget(QtWidgets.QLabel(endString,self),y+4,1)
					layout.addWidget(QtWidgets.QLabel('  Peak Width', self),y+5,0)
					layout.addWidget(QtWidgets.QLabel(widthString, self),y+5,1)

				self.setLayout(layout)

	def __init__(self, *args):
		"""
		constructor
		"""

		QtWidgets.QScrollArea.__init__(self, *args)
		self.logger = logging.getLogger('ScopeOut.scopeWidgets.waveColumnWidget')

		self.items = 0
		self.hold = False # Governs whether multiple waves can be active at once

		self.layout = QtWidgets.QVBoxLayout(self)
		self.layout.setContentsMargins(0,0,0,0)
		self.layout.setSpacing(0)
		self.layout.addStretch(0)

		container = ScopeOutWidget(self)
		container.setLayout(self.layout)
		
		self.setWidget(container)
		self.setWidgetResizable(True)

		self.addShadow()

		self.show()

	def addItem(self, item):
		"""
		Add a waveColumnItem to the column and display it.
		"""

		self.resetColors()
		item.setProperty('state','active')
		self.layout.insertWidget(0,item)
		self.show()
		item.waveSignal.connect(self.waveSignal)
		item.waveSignal.connect(self.resetColors)
		item.saveSignal.connect(self.saveSignal)
		item.savePropsSignal.connect(self.savePropsSignal)

	def addWave(self, wave):
		"""
		Receive a wave dict, package it as a waveColumnItem, and add it to the column.

		Parameters:
			:wave: a wave dictionary object.
		"""

		self.items += 1
		self.addItem(self.waveColumnItem(wave, self.items))

	def reset(self):
		"""
		Clear all waves from the list
		"""

		self.logger.info("Resetting Wave Column")
		while self.items:
			try:
				i = self.layout.takeAt(0)
				i.widget().hide()
				del i
				self.items -= 1
			except Exception as e:
				self.logger.error(e)
				break

		self.show()

	def resetColors(self):
		"""
		Turn all of the wave items back to the default color
		"""
		if not self.hold:  # Only reset the column if we're not showing multiple plots
			for i in range(0, self.layout.count()-1):
				w = self.layout.itemAt(i).widget()
				w.setProperty('state','inactive')
				w.style().unpolish(w)
				w.style().polish(w)
				w.update()

	def setHold(self, bool):
		"""
		Sets the hold variable, which governs whether or not multiple waves can be active
		at once. Called by a signal from the check box in the acqControlWidget.

		Parameters:
			:bool: Boolean value for self.hold.
		"""

		self.hold = bool
