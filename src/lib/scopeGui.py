"""
ScopeOut GUI

File to define relevant classes and widgets for user interface.
"""

from PyQt5 import QtGui, QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from lib.scopeUtils import ScopeFinder as sf
import sys, threading, numpy as np

class scopeOutMainWindow(QtWidgets.QMainWindow):
	"""
	Class to represent entire GUI Window. Will contain various QWidgets within a QLayout,
	menu bars, tool bars, etc.
	"""

	def __init__(self, widgets, *args):
		"""
		Constructor.
		will be passed widgets from threaded client (probably as array).
		"""
		self.widgets = widgets

		QtWidgets.QMainWindow.__init__(self, *args)

		self.central = QtWidgets.QWidget(self)
		self.layout = QtWidgets.QGridLayout(self)
		self.layout.addWidget(self.widgets[0],0,0)
		self.layout.addWidget(self.widgets[1],0,1)
		self.central.setLayout(self.layout)
		self.setCentralWidget(self.central)

		self.initUI()

	def initUI(self):

		# File->Exit
		exitAction = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)        
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.closeEvent)

        # Graph->Reset
		resetAction = QtWidgets.QAction('&Reset plot', self)
		resetAction.setShortcut('Ctrl+R')
		resetAction.setStatusTip('Reset plot and clear temperature data')
		# resetAction.triggered.connect(self.plotResetEvent)

        # Put title on window
		self.setWindowTitle('ScopeOut')

        # Initialize status bar at bottom of window
		self.statusBar().showMessage("Initializing")

        # Initialize "File" Section of top menu
		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(exitAction)
    
	def closeEvent(self, ev):
		"""
		Executed when window is closed or File->Exit is called.

		:ev:
			The CloseEvent in question. This is accepted by default.
		"""
		ev.accept()
		self.close()

	def setEnabled(self, bool):
		"""
		Enable/disable this widget.

		Parameters:
			:bool: True to enable, false to disable.
		"""

		for widget in self.widgets:
			widget.setEnabled(bool)
		print("Should be enabled")

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

	def __init__(self, scope, *args):

		self.scope = scope

		QtWidgets.QWidget.__init__(self, *args)

		self.acqButton = QtWidgets.QPushButton('Acquire',self)
		self.acqButton.setEnabled(False)
		if self.scope is not None:
			self.acqButton.setEnabled(True)

		self.layout = QtWidgets.QGridLayout(self)
		self.layout.addWidget(self.acqButton,0,0)
		self.show()



class ThreadedClient:
	"""
	Launches the GUI and handles I/O.

	GUI components reside within the body of the class itself, while actual serial communication
	is in a separate thread.
	"""

	def __init__(self):
		"""
		Constructor
		"""

		self.scopes = sf().getScopes();
		if(self.scopes):
			self.activeScope = self.scopes[0]
		else:
			self.activeScope = None
			self.scopeThread = threading.Thread(target=self.__scopeFind)
			self.scopeThread.start()

		self.scopeControl = scopeControlWidget(self.activeScope)
		self.plot = WavePlotWidget()
		self.mainWindow = scopeOutMainWindow([self.plot,self.scopeControl])
		self.__connectSignals()
		self.mainWindow.show()

	def __connectSignals(self):
		"""
		Connects signals from subwidgets to appropriate slots.
		"""

		self.scopeControl.acqButton.clicked.connect(self.__acqEvent)

	def __acqEvent(self):
		"""
		Executed to collect waveform data from scope.
		"""
		if self.activeScope is None: return
		
		self.mainWindow.statusBar().showMessage('Acquiring data...')
		self.activeScope.makeWaveform()
		wave = self.activeScope.getNextWaveform();
		if wave is not None:
			self.plot.showPlot(wave['xData'],wave['xUnit'],wave['yData'],wave['yUnit'])
		self.mainWindow.statusBar().showMessage('Waveform acquired on ' +wave['dataChannel'])

	def __scopeFind(self):
		"""
		Continually checks for connected scopes.
		"""
		while not self.scopes:
			self.scopes = sf().getScopes()

		self.activeScope = self.scopes[0]
		self.scopeControl = scopeControlWidget(self.activeScope)
		self.mainWindow.statusBar().showMessage('Found ' + str(self.activeScope))
		self.mainWindow.widgets[1].acqButton.setEnabled(True)


