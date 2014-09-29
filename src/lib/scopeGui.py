"""
ScopeOut GUI

File to define relevant classes and widgets for user interface.
"""

from PyQt5 import QtGui, QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import lib.oscilloscopes, sys

class scopeOutMainWindow(QtWidgets.QMainWindow):
	"""
	Class to represent entire GUI Window. Will contain various QWidgets within a QLayout,
	menu bars, tool bars, etc.
	"""

	def __init__(self, *args):
		"""
		Constructor.
		will be passed widgets from threaded client (probably as array).
		"""

		QtWidgets.QMainWindow.__init__(self, *args)

		self.graph = MplCanvasWidget()
		self.setCentralWidget(self.graph)

		self.initUI()
		self.show()

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
		self.close()


class MplCanvasWidget(FigureCanvas):
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
        self.axes.set_ylabel(yLabel)
        self.axes.set_xlabel(xLabel)

        # rudimentary auto-scaling
        self.axes.set_ylim([np.amin(yArray)-5,np.amax(yArray)+5])

        self.axes.plot(xData,yData)
        self.axes.legend()
        self.fig.canvas.draw()

