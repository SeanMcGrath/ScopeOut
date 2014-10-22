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
import os, re, numpy as np


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
		saveAction = QtWidgets.QAction(QtGui.QIcon('save.png'), '&Save Waveform', self)
		saveAction.setShortcut('Ctrl+S')
		saveAction.setStatusTip('Save Waveform to .csv file')
		saveAction.triggered.connect(self.saveCommand)

		# Data->Reset
		self.resetAction = QtWidgets.QAction('&Reset and Clear Data', self)
		self.resetAction.setShortcut('Ctrl+R')
		self.resetAction.setStatusTip('Clear all waveforms in memory')

        # Put title on window
		self.setWindowTitle('ScopeOut')

        # Initialize status bar at bottom of window
		self.statusBar().showMessage("Initializing")

        # Initialize "File" Section of top menu
		self.menubar = self.menuBar()
		self.fileMenu = self.menubar.addMenu('&File')
		self.fileMenu.addAction(exitAction)
		self.fileMenu.addAction(saveAction)
		self.dataMenu = self.menubar.addMenu('&Data')
		self.dataMenu.addAction(self.resetAction)
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
						print('Could not process ' + theme + ', ignoring')
		except Exception as e:
			print(e)
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

		self.menubar.actions()[1].setEnabled(bool)
		self.menubar.actions()[0].menu().actions()[1].setEnabled(bool)

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

	def resetPlot(self):
		"""
		Reset plot to initial state.
		"""

		self.axes.clear()
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
		self.setLayout(self.layout)

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
			self.channelComboBox.addItem('All')
		else:
			self.channelComboBox.clear()