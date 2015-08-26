"""
ScopeOut Widgets

Widget classes for Scopeout GUI.

Sean McGrath, 2014
"""

import os
import re
import logging
from numpy import multiply, amax

from PyQt5 import QtGui, QtWidgets, QtCore
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from collections import OrderedDict
from functools import partial

from scopeout.oscilloscopes import GenericOscilloscope
from scopeout.config import ScopeOutConfig as Config
from scopeout.models import *


class ScopeOutWidget(QtWidgets.QWidget):
    """
    Base class for the QWidgets that make up the ScopeOut interface.
    Provides methods important to the consistent styling of the application.
    """

    time_units = OrderedDict([('nS', 1e-9), ('uS', 1e-6), ('mS', 1e-3), ('S', 1)])
    voltage_units = OrderedDict([('nV', 1e-9), ('uV', 1e-6), ('mV', 1e-3), ('V', 1)])

    def __init__(self, *args):

        QtWidgets.QWidget.__init__(self, *args)

        # Just add actions to the widget to get right click menus
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def add_shadow(self, widget=None):
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

    def add_shadow(self, widget=None):
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

    def __init__(self):
        """
        Constructor

        Parameters:
            :figure: a matplotlib figure to be displayed.
        """

        self.logger = logging.getLogger("ScopeOut.widgets.ScopeOutPlotWidget")

        self.fig = Figure()
        self.fig.patch.set_alpha(0.0)

        FigureCanvas.__init__(self, self.fig)

        self.axes = self.fig.add_subplot(111)
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')
        self.coords = self.axes.text(0, 0, '')
        [t.set_color('white') for t in self.axes.yaxis.get_ticklabels()]
        [t.set_color('white') for t in self.axes.xaxis.get_ticklabels()]

        self.nav_toolbar = NavigationToolbar(self, self, False)

        self.setContentsMargins(5, 5, 5, 5)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def display_coords(self, event):
        """
        display the coordinates of the mouse on the graph.

        Parameters:
            :event: an event object containing the mouse location data.
        """

        if event.inaxes:
            event_string = 'x: {} {}   y: {} {}'.format(
                round(event.xdata, 5), self.axes.get_xlabel(), round(event.ydata, 5), self.axes.get_ylabel())
            self.coords.remove()
            self.coords = self.axes.text(0.05, 0.95, event_string, ha='left', va='center', transform=self.axes.transAxes)
            self.fig.canvas.draw()

    @staticmethod
    def autoset_units(axis_array):
        """
        Set the X time_units of the plot to the correct size based on the values in axisArray.

        Parameters:
            :axisArray: the array of values representing one dimension of the waveform.
        """
        x_max = amax(axis_array)
        if x_max > 1e-9:
            if x_max > 1e-6:
                if x_max > 1e-3:
                    if x_max > 1:
                        prefix = ''
                        return axis_array, prefix

                    prefix = 'milli'
                    axis_array = multiply(axis_array, 1000)
                    return axis_array, prefix

                prefix = 'micro'
                axis_array = multiply(axis_array, 1e6)
                return axis_array, prefix

            prefix = 'nano'
            axis_array = multiply(axis_array, 1e9)
            return axis_array, prefix

        prefix = ''
        return axis_array, prefix

    def reset_plot(self):
        """
        Reset plot to initial state.
        """

        self.axes.clear()
        self.axes = self.fig.add_subplot(111)
        [t.set_color('white') for t in self.axes.yaxis.get_ticklabels()]
        [t.set_color('white') for t in self.axes.xaxis.get_ticklabels()]
        self.coords = self.axes.text(0, 0, '')
        self.fig.canvas.draw()
        self.logger.info("Plot Reset")

    def save_plot(self, filename):
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

    def set_title(self, title):
        """
        Set the title of the histogram.
        :param title: a new title string.
        """

        assert isinstance(title, str)
        self.fig.suptitle(title.title().replace('_', ' '), color='white')

    def set_patch_color(self, color):
        self.fig.patch.set_color(color)


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

        self.logger = logging.getLogger('ScopeOut.widgets.ScopeOutMainWindow')
        self.logger.info('Main Window created')

        self.widgets = widgets

        self.end_command = commands['end']

        self.central_widget = QtWidgets.QWidget(self)
        self.layout = QtWidgets.QGridLayout(self.central_widget)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(WaveColumnHeader(), 0, 0)
        self.layout.addWidget(self.widgets['column'], 1, 0, -1, 1)
        self.layout.addWidget(self.widgets['plot'], 2, 2, 1, 1)
        self.layout.addWidget(self.widgets['hist'], 2, 3, 1, 1)
        self.layout.addWidget(self.widgets['acqControl'], 0, 5, -1, 1)
        self.layout.addWidget(self.widgets['wave_options'], 4, 2)
        self.layout.addWidget(self.widgets['hist_options'], 4, 3)
        self.layout.setColumnMinimumWidth(1, 20)
        self.layout.setColumnMinimumWidth(2, 500)
        self.layout.setColumnMinimumWidth(3, 500)
        self.layout.setColumnMinimumWidth(4, 20)
        self.layout.setColumnMinimumWidth(5, 180)
        self.layout.setColumnStretch(1, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(3, 1)
        self.layout.setRowStretch(5, 1)
        self.layout.setRowMinimumHeight(3, 20)
        self.layout.setRowMinimumHeight(5, 20)
        self.layout.setRowMinimumHeight(2, 500)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

        self.initialize_ui_elements()

        self.setEnabled(False)

    def initialize_ui_elements(self):
        """
        Construct non-widget UI elements - Menubar, statusbar, etc. Load theme
        """

        self.initialize_theme()

        # File->Exit
        exit_action = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.closeEvent)

        # File->Save
        self.save_action = QtWidgets.QAction(QtGui.QIcon('save.png'), '&Save Waveforms', self)
        self.save_action.setShortcut('Ctrl+S')
        self.save_action.setStatusTip('Save all acquired waveforms to .csv file')

        # File-> Save Properties
        self.save_properties_action = QtWidgets.QAction(QtGui.QIcon('save.png'), 'Save Waveform Properties', self)
        self.save_properties_action.setShortcut('Ctrl+Alt+S')
        self.save_properties_action.setStatusTip('Save desired properties of waveforms to .csv file')

        # File->Save Plot
        self.save_plot_action = QtWidgets.QAction(QtGui.QIcon('save.png'), 'Save Plot', self)
        self.save_plot_action.setStatusTip('Save plot image to a file.')

        # File->Save Histogram
        self.save_histogram_action = QtWidgets.QAction(QtGui.QIcon('save.png'), 'Save Histogram', self)
        self.save_histogram_action.setStatusTip('Save histogram image to a file.')

        # File->Load Session
        self.load_session_action = QtWidgets.QAction(QtGui.QIcon('load.png'), '&Load Session', self)
        self.load_session_action.setShortcut('Ctrl+L')
        self.save_action.setStatusTip('Load waveforms from a past data acquisition session.')

        # File->Save settings
        self.save_settings_action = QtWidgets.QAction('Save Settings as Defaults', self)
        self.save_settings_action.setStatusTip('Save the current application settings as the default configuration.')

        # Data->Reset
        self.reset_action = QtWidgets.QAction('&Reset and Clear Data', self)
        self.reset_action.setShortcut('Ctrl+R')
        self.reset_action.setStatusTip('Clear all waveforms in memory')

        # View->Show Waveform Plot
        self.show_plot_action = QtWidgets.QAction('Show waveform plot', self)
        self.show_plot_action.setCheckable(True)
        self.show_plot_action.setChecked(Config.get_bool('View', 'show_plot'))

        # View->Show Histogram
        self.show_histogram_action = QtWidgets.QAction('Show histogram', self)
        self.show_histogram_action.setCheckable(True)
        self.show_histogram_action.setChecked(Config.get_bool('View', 'show_histogram'))

        # Put title on window
        self.setWindowTitle('ScopeOut')

        # Initialize status bar at bottom of window
        self.statusBar().showMessage("Initializing")

        # Initialize "File" Section of top menu
        self.menubar = self.menuBar()
        self.file_menu = self.menubar.addMenu('&File')
        self.file_menu.addAction(exit_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_properties_action)
        self.file_menu.addAction(self.save_plot_action)
        self.file_menu.addAction(self.save_histogram_action)
        self.file_menu.addAction(self.load_session_action)
        self.file_menu.addAction(self.save_settings_action)

        # "Data" Menu
        self.data_menu = self.menubar.addMenu('&Data')
        self.data_menu.addAction(self.reset_action)

        # "View" Menu
        view_menu = self.menubar.addMenu('&View')
        theme_menu = view_menu.addMenu('Change Theme')
        if self.themes:
            for theme in self.themes:
                theme_action = QtWidgets.QAction(theme.split('\\')[-1].split('.')[0], self)
                theme_action.setStatusTip('Change active theme to ' +
                                          theme.split('\\')[-1].split('.')[0] + ' (' + theme + ')')
                theme_action.triggered.connect(partial(self.load_theme, theme))
                theme_menu.addAction(theme_action)
        else:
            theme_menu.setEnabled(False)

        view_menu.addSeparator()
        view_menu.addAction(self.show_plot_action)
        view_menu.addAction(self.show_histogram_action)

    def initialize_theme(self):
        """
        Finds all themes, and loads first available one.
        """

        def find_themes():
            """
            Finds themes (stylesheets) in the Themes folder, currently '\lib\Themes'
            and stores their paths in self.themes.

            :Returns: themes, the array of theme paths, for convenience.
            """

            config_path = Config.get('Themes', 'theme_dir')
            local_path = os.path.join(os.getcwd(), 'themes')
            paths = [config_path, local_path, os.getcwd()]
            themes = []

            for path in paths:
                try:
                    theme_files = os.listdir(path)
                    themes += [os.path.join(path, theme)
                              for theme in theme_files if re.match('.*stylesheet', theme)]
                except Exception as e:
                    self.logger.error(e)

            return list(set(themes))

        self.themes = find_themes()
        if self.themes:
            i = 0
            while True:
                if i > len(self.themes) - 1:
                    break
                elif self.load_theme(self.themes[i]):
                    self.logger.info("Loaded theme %s", self.themes[i])
                    break
                else:
                    i += 1

    def load_theme(self, theme_path):
        """
        Loads style sheet from themePath and sets it as the application's style.

        Parameters:
            :themePath: the absolute path to a styesheet defining a theme.

        :Returns: True if theme is loaded successfully, False otherwise.
        """

        try:
            style = open(theme_path, 'r')
            self.setStyleSheet('')
            self.setStyleSheet(style.read())
            self.update()
        except Exception as e:
            self.logger.error(theme_path + ' could not be loaded')
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
        self.end_command()
        self.close()

    def setEnabled(self, enabled):
        """
        Enable/disable this widget.

        Parameters:
            :enabled: True to enable, false to disable.
        """

        if enabled:
            self.logger.info("Main Window enabled")
        else:
            self.logger.info("Main Window disabled")

        self.widgets['acqControl'].setEnabled(enabled)

    def status(self, message):
        """
        print a message to the status bar.

        Parameters:
            :message: The string to be displayed.
        """

        self.statusBar().showMessage(message)

    def select_plot_type(self, histogram):
        """
        Switch between display of histogram and wave plots.

        Parameters:
            :bool: true to display histogram, false for wave plot.
        """

        if histogram:
            self.widgets['plot'].hide()
            self.layout.replaceWidget(self.widgets['plot'], self.widgets['hist'])
            self.widgets['hist'].show()

        else:
            self.widgets['hist'].hide()
            self.layout.replaceWidget(self.widgets['hist'], self.widgets['plot'])
            self.widgets['plot'].show()


class WavePlotWidget(ScopeOutWidget):
    """
    Class to hold matplotlib Figures for display.
    """

    def __init__(self):
        """
        Constructor
        """

        ScopeOutWidget.__init__(self)
        self.logger = logging.getLogger("ScopeOut.widgets.WavePlotWidget")
        self.plot = ScopeOutPlotWidget()
        self.plot.fig.suptitle("Waveform Capture", color='white')
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.plot)
        self.layout.addWidget(self.plot.nav_toolbar)
        self.layout.setAlignment(self.plot.nav_toolbar, QtCore.Qt.AlignCenter)
        self.setLayout(self.layout)
        self.logger.info("Wave Plot initialized")

        self.save_plot_action = QtWidgets.QAction('Save Plot', self)
        self.addAction(self.save_plot_action)

        self.setEnabled(Config.get_bool('View', 'show_plot'))

    def show_plot(self, wave, hold=False, show_peak=False):
        """
        Plot a waveform to the screen.
        :param wave: a Waveform object to plot.
        :param hold: true to draw on top of the old plot, false to draw a new plot.
        :param show_peak: true to show the peak window.
        """

        if not hold:
            self.plot.reset_plot()

        self.plot.fig.suptitle("Waveform Capture", color='white')

        x_data, x_prefix = self.plot.autoset_units(wave.x_list)
        y_data, y_prefix = self.plot.autoset_units(wave.y_list)
        self.plot.axes.set_ylabel(y_prefix + wave.y_unit)
        self.plot.axes.set_xlabel(x_prefix + wave.x_unit)
        self.plot.axes.plot(x_data, y_data)
        if show_peak and wave.peak_start >= 0:
            self.plot_vertical_lines([wave.x_list[wave.peak_start], wave.x_list[wave.peak_end]])
        cursor = Cursor(self.plot.axes, useblit=True, color='black', linewidth=1)
        cursor.connect_event('motion_notify_event', self.plot.display_coords)
        self.plot.fig.canvas.draw()

        self.logger.info('plotting completed')

    def plot_vertical_lines(self, x_array):
        """
        Add vertical lines at the x values in x_array.

        Parameters:
            :x_array: the list of x values at which to add vertical lines
        """

        x_array, prefix = self.plot.autoset_units(x_array)
        for x in x_array:
            if x >= 0:
                self.plot.axes.axvline(x)

        self.logger.info("drew vertical lines")

    def setEnabled(self, bool):

        self.plot.reset_plot()
        super().setEnabled(bool)
        if not bool:
            self.plot.axes.patch.set_facecolor('gray')
        elif bool:
            self.plot.axes.patch.set_facecolor('white')
        self.plot.draw()


class HistogramPlotWidget(ScopeOutWidget):
    """
    Widget holding a matplotlib histogram.
    """

    def __init__(self):
        """
        Constructor
        """

        ScopeOutWidget.__init__(self)
        self.logger = logging.getLogger("ScopeOut.widgets.HistogramPlotWidget")
        self.histogram = ScopeOutPlotWidget()
        self.histogram.fig.suptitle("Histogram", color='white')

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.histogram)
        self.layout.addWidget(self.histogram.nav_toolbar)
        self.layout.setAlignment(self.histogram.nav_toolbar, QtCore.Qt.AlignCenter)
        self.logger.info("Histogram Plot initialized")

        self.save_histogram_action = QtWidgets.QAction('Save Histogram', self)
        self.addAction(self.save_histogram_action)

        self.setEnabled(Config.get_bool('View', 'show_histogram'))

    def show_histogram(self, x, bins):
        """
        Plot the histogram of integrated wave values.

        Parameters:
            :x: the histogram x data.
            :bins: the number of bins desired.
        """

        if len(x) > 1:
            self.histogram.reset_plot()
            self.histogram.axes.hist(x, bins)
            self.histogram.axes.set_ylabel('Counts')
            self.histogram.fig.canvas.draw()

    def reset(self):
        """
        Reset the widget to its initial state.
        """

        self.histogram.set_title('Histogram')
        self.histogram.reset_plot()

    def setEnabled(self, bool):

        self.histogram.reset_plot()
        super().setEnabled(bool)
        if not bool:
            self.histogram.axes.patch.set_facecolor('gray')
        elif bool:
            self.histogram.axes.patch.set_facecolor('white')
        self.histogram.draw()


class AcquisitionControlWidget(ScopeOutWidget):
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
        self.logger = logging.getLogger('ScopeOut.widgets.acqControlWidget')

        self.scope = scope

        self.initialize_subwidgets()
        self.add_shadow()
        self.show()

    def initialize_subwidgets(self):
        """
        Set up the subwidgets
        """

        self.acquire_button = QtWidgets.QPushButton('Acquire', self)
        self.continuous_acquire_button = QtWidgets.QPushButton('Acquire Continuously', self)
        self.autoset_button = QtWidgets.QPushButton('Autoset', self)
        self.acquire_on_trigger_button = QtWidgets.QPushButton('Acquire on Trigger', self)
        self.stop_acquisition_button = QtWidgets.QPushButton('Stop Acquisition', self)
        self.stop_acquisition_button.setProperty('type', 'stop')
        self.hold_plot_checkbox = QtWidgets.QCheckBox('Hold Plot', self)

        try:
            plot_held = Config.get('Acquisition Control', 'hold_plot')
            self.hold_plot_checkbox.setChecked(plot_held.lower() in ['true', 't', '1'])
        except Exception as e:
            self.logger.error(e)

        self.show_peak_checkbox = QtWidgets.QCheckBox('Show Peak Window', self)

        try:
            show_peak = Config.get('Acquisition Control', 'show_peak')
            self.show_peak_checkbox.setChecked(show_peak.lower() in ['true', 't', '1'])
        except Exception as e:
            self.logger.error(e)

        self.channel_combobox_label = QtWidgets.QLabel('Data Channel', self)
        self.channel_combobox = QtWidgets.QComboBox(self)

        if self.scope is not None:
            self.setEnabled(True)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addStretch(1)
        self.layout.addWidget(self.autoset_button)
        self.layout.addStretch(1)
        self.layout.addWidget(self.acquire_button)
        self.layout.addWidget(self.acquire_on_trigger_button)
        self.layout.addWidget(self.continuous_acquire_button)
        self.layout.addWidget(self.stop_acquisition_button)
        self.layout.addSpacing(15)
        self.layout.addWidget(self.hold_plot_checkbox)
        self.layout.addWidget(self.show_peak_checkbox)
        self.layout.addStretch(1)
        self.layout.addWidget(self.channel_combobox_label)
        self.layout.addWidget(self.channel_combobox)
        self.layout.setAlignment(self.channel_combobox, QtCore.Qt.AlignCenter)
        self.layout.setAlignment(self.channel_combobox_label, QtCore.Qt.AlignCenter)
        self.layout.addStretch(1)
        self.setLayout(self.layout)

        for i in range(0, self.layout.count()):
            self.add_shadow(self.layout.itemAt(i).widget())

    @property
    def show_peak_window(self):
        """
        :Returns: the boolean value of "show peak start" checkbox.
        """

        return self.show_peak_checkbox.isChecked()

    def set_active_oscilloscope(self, scope):
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

        self.acquire_button.setEnabled(bool)
        self.autoset_button.setEnabled(bool)
        self.channel_combobox.setEnabled(bool)
        self.acquire_on_trigger_button.setEnabled(bool)
        self.continuous_acquire_button.setEnabled(bool)
        self.stop_acquisition_button.setEnabled(False)
        if bool and self.scope is not None:
            channels = list(map(str, range(1, self.scope.numChannels + 1)))
            channels.append('All')
            channels.append('Math')
            self.channel_combobox.addItems(channels)

            try:
                channel = Config.get('Acquisition Control', 'data_channel')
                index = self.channel_combobox.findText(channel)
                self.channel_combobox.setCurrentIndex(index)
            except Exception as e:
                self.logger.error(e)
                self.channel_combobox.setCurrentIndex(0)

        elif bool:  # Wait for scope to become active
            while self.scope is None:
                pass
            channels = list(map(str, range(1, self.scope.numChannels + 1)))
            channels.append('All')
            channels.append('Math')
            self.channel_combobox.addItems(channels)
            self.channel_combobox.setCurrentIndex(0)
        else:
            self.channel_combobox.clear()

    @property
    def plot_held(self):
        """
        Check if 'plot hold' option is selected.

        :Returns: True if plot is to be held, false otherwise
        """

        return self.hold_plot_checkbox.isChecked()

    @property
    def data_channels(self):
        """
        Returns a list of the available data channels.
        """

        return [self.channel_combobox.itemText(i) for i in range(self.channel_combobox.count())]

    def enable_buttons(self, bool):
        """
        Enable/disable acquisition buttons as appropriate depending on the
        current more of operation, e.g. disable 'stop acquisition' button
        until an acquisition has started.
        """

        self.acquire_button.setEnabled(bool)
        self.continuous_acquire_button.setEnabled(bool)
        self.autoset_button.setEnabled(bool)
        self.acquire_on_trigger_button.setEnabled(bool)
        self.stop_acquisition_button.setEnabled(not bool)


class WaveOptionsTabWidget(ScopeOutWidget):
    """
    Manages tabbed display of wave options widgets.
    """

    class SmartPeakTab(ScopeOutWidget):
        """
        Widget controlling smart peak detection algorithm.
        """

        def __init__(self, *args):
            """
            constructor.
            """

            self.logger = logging.getLogger('ScopeOut.widgets.SmartPeakTab')
            ScopeOutWidget.__init__(self, *args)
            self.initialize_subwidgets()
            self.show()

        def initialize_subwidgets(self):
            """
            Set up sub-widgets.
            """

            self.start_threshold_label = QtWidgets.QLabel("Peak Start Threshold", self)
            self.end_threshold_label = QtWidgets.QLabel("Peak End Threshold", self)
            self.start_threshold_input = QtWidgets.QSpinBox(self)
            self.start_threshold_input.setMaximum(500)
            self.start_threshold_input.setMinimum(0)
            self.start_threshold_input.setSuffix('%')

            try:
                start_threshold = float(Config.get('Peak Detection', 'smart_start_threshold'))
                self.start_threshold_input.setValue(start_threshold)
            except Exception as e:
                self.logger.error(e)

            self.end_threshold_input = QtWidgets.QDoubleSpinBox(self)
            self.end_threshold_input.setMaximum(500.0)
            self.end_threshold_input.setMinimum(0.0)
            self.end_threshold_input.setSuffix('%')

            try:
                end_threshold = float(Config.get('Peak Detection', 'smart_end_threshold'))
                self.end_threshold_input.setValue(end_threshold)
            except Exception as e:
                self.logger.error(e)

            self.layout = QtWidgets.QGridLayout(self)

            self.layout.addWidget(self.start_threshold_label, 0, 1)
            self.layout.addWidget(self.start_threshold_input, 0, 2)
            self.layout.addWidget(self.end_threshold_label, 1, 1)
            self.layout.addWidget(self.end_threshold_input, 1, 2)
            self.layout.setColumnStretch(0, 1)
            self.layout.setColumnStretch(3, 1)
            self.setLayout(self.layout)

        @property
        def peak_detection_parameters(self):
            """
            Returns the peak thresholds as decimals.

            :Returns: An array containing the start threshold followed by the end threshold.
            """

            return [self.start_threshold_input.value() / 100.0, self.end_threshold_input.value() / 100.0]

        def setEnabled(self, bool):
            """
            Enable/disable this widget.

            Parameters:
                :bool: True to  enable, false to disable.
            """

            self.start_threshold_input.setEnabled(bool)
            self.end_threshold_input.setEnabled(bool)

    class FixedPeakTab(ScopeOutWidget):
        """
        Widget controlling Fixed-width peak detection algorithm.
        """

        def __init__(self, *args):
            """
            constructor.
            """

            self.logger = logging.getLogger('ScopeOut.widgets.FixedPeakTab')
            ScopeOutWidget.__init__(self, *args)
            self.initialize_subwidgets()
            self.show()

        def initialize_subwidgets(self):
            """
            Set up sub-widgets.
            """

            self.start_time_label = QtWidgets.QLabel("Peak Start Time", self)
            self.peak_width_label = QtWidgets.QLabel("Peak Width", self)
            self.start_time_input = QtWidgets.QDoubleSpinBox(self)
            self.start_time_input.setMaximum(1000)
            self.start_time_input.setMinimum(0)

            try:
                start_time = float(Config.get('Peak Detection', 'fixed_start_time'))
                self.start_time_input.setValue(start_time)
            except Exception as e:
                self.logger.error(e)

            self.start_time_unit_combobox = QtWidgets.QComboBox(self)
            self.start_time_unit_combobox.addItems(self.time_units.keys())

            try:
                unit = Config.get('Peak Detection', 'fixed_start_unit')
                index = self.start_time_unit_combobox.findText(unit)
                self.start_time_unit_combobox.setCurrentIndex(index)
            except Exception as e:
                self.logger.error(e)

            self.peak_width_input = QtWidgets.QDoubleSpinBox(self)
            self.peak_width_input.setMaximum(1000)
            self.peak_width_input.setMinimum(0)

            try:
                width = float(Config.get('Peak Detection', 'fixed_width_time'))
                self.peak_width_input.setValue(width)
            except Exception as e:
                self.logger.error(e)

            self.peak_width_unit_combobox = QtWidgets.QComboBox(self)
            self.peak_width_unit_combobox.addItems(self.time_units.keys())

            try:
                unit = Config.get('Peak Detection', 'fixed_width_unit')
                index = self.peak_width_unit_combobox.findText(unit)
                self.peak_width_unit_combobox.setCurrentIndex(index)
            except Exception as e:
                self.logger.error(e)

            self.layout = QtWidgets.QGridLayout(self)
            self.layout.setContentsMargins(20, 5, 20, 5)
            self.layout.setHorizontalSpacing(20)

            self.layout.addWidget(self.start_time_label, 0, 1)
            self.layout.addWidget(self.start_time_input, 0, 2)
            self.layout.addWidget(self.start_time_unit_combobox, 0, 3)
            self.layout.addWidget(self.peak_width_label, 1, 1)
            self.layout.addWidget(self.peak_width_input, 1, 2)
            self.layout.addWidget(self.peak_width_unit_combobox, 1, 3)
            self.layout.setColumnStretch(0, 1)
            self.layout.setColumnStretch(4, 1)
            self.setLayout(self.layout)

        @property
        def peak_detection_parameters(self):
            """
            Returns the peak thresholds as decimals.

            :Returns: An array containing the peak start time and the peak width in seconds
            """

            return [self.start_time_input.value() * self.time_units[self.start_time_unit_combobox.currentText()],
                    self.peak_width_input.value() * self.time_units[self.peak_width_unit_combobox.currentText()]]

        def setEnabled(self, bool):
            """
            Enable/disable this widget.

            Parameters:
                :bool: True to enable, false to disable.
            """

            self.start_threshold_input.setEnabled(bool)
            self.end_threshold_input.setEnabled(bool)

    class HybridPeakTab(ScopeOutWidget):
        """
        Widget controlling hybrid peak detection algorithm.
        """

        def __init__(self, *args):
            """
            constructor.
            """

            self.logger = logging.getLogger('ScopeOut.widgets.HybridPeakTab')
            ScopeOutWidget.__init__(self, *args)
            self.initialize_subwidgets()
            self.show()

        def initialize_subwidgets(self):
            """
            Set up sub-widgets.
            """

            self.start_threshold_label = QtWidgets.QLabel("Peak Start Threshold", self)
            self.peak_width_label = QtWidgets.QLabel("Peak Width", self)
            self.start_threshold_input = QtWidgets.QSpinBox(self)
            self.start_threshold_input.setMaximum(500)
            self.start_threshold_input.setMinimum(0)
            self.start_threshold_input.setSuffix('%')

            try:
                start_threshold = float(Config.get('Peak Detection', 'hybrid_start_threshold'))
                self.start_threshold_input.setValue(start_threshold)
            except Exception as e:
                self.logger.error(e)

            self.peak_width_input = QtWidgets.QDoubleSpinBox(self)
            self.peak_width_input.setMaximum(1000)
            self.peak_width_input.setMinimum(0)

            try:
                width = float(Config.get('Peak Detection', 'hybrid_width_time'))
                self.peak_width_input.setValue(width)
            except Exception as e:
                self.logger.error(e)

            self.peak_width_units = QtWidgets.QComboBox(self)
            self.peak_width_units.addItems(self.time_units.keys())

            try:
                unit = Config.get('Peak Detection', 'hybrid_width_unit')
                index = self.peak_width_units.findText(unit)
                self.peak_width_units.setCurrentIndex(index)
            except Exception as e:
                self.logger.error(e)

            self.layout = QtWidgets.QGridLayout(self)
            self.layout.setContentsMargins(20, 5, 20, 5)
            self.layout.setHorizontalSpacing(20)

            self.layout.addWidget(self.start_threshold_label, 0, 1)
            self.layout.addWidget(self.start_threshold_input, 0, 2)
            self.layout.addWidget(self.peak_width_label, 1, 1)
            self.layout.addWidget(self.peak_width_input, 1, 2)
            self.layout.addWidget(self.peak_width_units, 1, 3)
            self.layout.setColumnStretch(0, 1)
            self.layout.setColumnStretch(0, 4)
            self.setLayout(self.layout)

        @property
        def peak_detection_parameters(self):
            """
            Returns the peak thresholds as decimals.

            :Returns: An array containing the peak start time and the peak width in seconds
            """

            return [self.start_threshold_input.value() / 100.0,
                    self.peak_width_input.value() * self.time_units[self.peak_width_units.currentText()]]

        def setEnabled(self, bool):
            """
            Enable/disable this widget.

            Parameters:
                :bool: True to enable, false to disable.
            """

            self.start_threshold_input.setEnabled(bool)
            self.endThresholdInput.setEnabled(bool)

    class VoltageThresholdTab(ScopeOutWidget):
        """
        Tab to manage the voltage  threshold peak detection method
        """

        def __init__(self, *args):
            """
            constructor.
            """

            self.logger = logging.getLogger('ScopeOut.widgets.VoltageThresholdTab')
            ScopeOutWidget.__init__(self, *args)
            self.initialize_subwidgets()
            self.show()

        def initialize_subwidgets(self):

            self.peak_start_label = QtWidgets.QLabel('Peak starts when voltage goes', self)
            self.start_above_below_combobox = QtWidgets.QComboBox(self)
            self.start_above_below_combobox.addItems(['above', 'below'])

            try:
                default_edge = Config.get('Peak Detection', 'voltage_threshold_start_edge')
                if default_edge:
                    default_index = self.start_above_below_combobox.findText(default_edge)
                    if default_index >= 0:
                        self.start_above_below_combobox.setCurrentIndex(default_index)
            except Exception as e:
                self.logger.error(e)

            self.start_voltage_spinbox = QtWidgets.QDoubleSpinBox(self)
            self.start_voltage_spinbox.setMinimum(-9999)
            self.start_voltage_spinbox.setMaximum(9999)

            try:
                default_value = Config.get('Peak Detection', 'voltage_threshold_start_value')
                if default_value:
                    self.start_voltage_spinbox.setValue(float(default_value))
            except Exception as e:
                self.logger.error(e)

            self.start_voltage_unit_combobox = QtWidgets.QComboBox(self)
            self.start_voltage_unit_combobox.addItems(self.voltage_units.keys())

            try:
                default_unit = Config.get('Peak Detection', 'voltage_threshold_start_unit')
                if default_unit:
                    default_index = self.start_voltage_unit_combobox.findText(default_unit)
                    if default_index >= 0:
                        self.start_voltage_unit_combobox.setCurrentIndex(default_index)
            except Exception as e:
                self.logger.error(e)

            self.peak_end_label = QtWidgets.QLabel('Peak ends when voltage goes', self)
            self.end_above_below_combobox = QtWidgets.QComboBox(self)
            self.end_above_below_combobox.addItems(['above', 'below'])

            try:
                default_edge = Config.get('Peak Detection', 'voltage_threshold_end_edge')
                if default_edge:
                    default_index = self.end_above_below_combobox.findText(default_edge)
                    if default_index >= 0:
                        self.end_above_below_combobox.setCurrentIndex(default_index)
            except:
                pass

            self.end_voltage_spinbox = QtWidgets.QDoubleSpinBox(self)
            self.end_voltage_spinbox.setMinimum(-9999)
            self.end_voltage_spinbox.setMaximum(9999)

            try:
                default_value = Config.get('Peak Detection', 'voltage_threshold_end_value')
                if default_value:
                    self.end_voltage_spinbox.setValue(float(default_value))
            except Exception as e:
                self.logger.error(e)

            self.end_voltage_unit_combobox = QtWidgets.QComboBox(self)
            self.end_voltage_unit_combobox.addItems(self.voltage_units.keys())

            try:
                default_unit = Config.get('Peak Detection', 'voltage_threshold_end_unit')
                if default_unit:
                    default_index = self.end_voltage_unit_combobox.findText(default_unit)
                    if default_index >= 0:
                        self.end_voltage_unit_combobox.setCurrentIndex(default_index)
            except Exception as e:
                self.logger.error(e)

            self.layout = QtWidgets.QGridLayout(self)
            self.layout.addWidget(self.peak_start_label, 0, 1)
            self.layout.addWidget(self.start_above_below_combobox, 0, 2)
            self.layout.addWidget(self.start_voltage_spinbox, 0, 3)
            self.layout.addWidget(self.start_voltage_unit_combobox, 0, 4)
            self.layout.addWidget(self.peak_end_label, 1, 1)
            self.layout.addWidget(self.end_above_below_combobox, 1, 2)
            self.layout.addWidget(self.end_voltage_spinbox, 1, 3)
            self.layout.addWidget(self.end_voltage_unit_combobox, 1, 4)
            self.layout.setColumnStretch(0, 1)
            self.layout.setColumnStretch(5, 1)
            self.setLayout(self.layout)

        @property
        def peak_detection_parameters(self):
            return (self.start_above_below_combobox.currentText(),
                    self.start_voltage_spinbox.value() * self.voltage_units[self.start_voltage_unit_combobox.currentText()],
                    self.end_above_below_combobox.currentText(),
                    self.end_voltage_spinbox.value() * self.voltage_units[self.end_voltage_unit_combobox.currentText()])

    def __init__(self, *args):
        """
        Constructor
        """

        self.logger = logging.getLogger('ScopeOut.widgets.waveOptionsTabWidget')
        ScopeOutWidget.__init__(self, *args)

        self.tab_manager = QtWidgets.QTabWidget(self)
        self.smart = self.SmartPeakTab(None)
        self.fixed = self.FixedPeakTab(None)
        self.hybrid = self.HybridPeakTab(None)
        self.voltage_threshold = self.VoltageThresholdTab(None)

        self.tab_titles = ['Smart', 'Fixed Width', 'Hybrid', 'Voltage Threshold']
        self.tab_manager.addTab(self.smart, self.tab_titles[0])
        self.tab_manager.addTab(self.fixed, self.tab_titles[1])
        self.tab_manager.addTab(self.hybrid, self.tab_titles[2])
        self.tab_manager.addTab(self.voltage_threshold, self.tab_titles[3])

        try:
            selected_tab = Config.get('Peak Detection', 'detection_method')
            tab_index = self.tab_titles.index(selected_tab)
            self.tab_manager.setCurrentIndex(tab_index)
        except Exception as e:
            self.logger.error(e)

        self.layout = QtWidgets.QGridLayout(self)

        self.layout.addWidget(QtWidgets.QLabel('Peak Detection Mode', self), 0, 0)
        self.layout.addWidget(self.tab_manager, 1, 0, 3, -1)
        self.layout.setRowMinimumHeight(0, 30)
        self.layout.setRowStretch(4, 1)
        self.layout.setVerticalSpacing(10)
        self.layout.setHorizontalSpacing(15)
        self.show()

    @property
    def current_widget(self):
        """
        :Returns: a widget object representing the currently displayed tab
        """

        return self.tab_manager.currentWidget()

    @property
    def peak_detection_parameters(self):
        """
        :Returns: the relevant peak-detection parameters from the current tab
        """

        return self.current_widget.peak_detection_parameters

    @property
    def peak_detection_mode(self):
        """
        :Returns: a string indicating the current peak detection mode
        """

        return self.tab_titles[self.tab_manager.currentIndex()]


class WaveColumnWidget(ScopeOutScrollArea):
    """
    A column display showing acquired waveforms.
    """

    wave_signal = QtCore.pyqtSignal(dict)  # signal to pass wave to plot
    save_signal = QtCore.pyqtSignal(dict)  # signal to pass wave to saving routine
    save_properties_signal = QtCore.pyqtSignal(dict)  # signal to pass wave to property saving routine
    delete_signal = QtCore.pyqtSignal(Waveform)  # Signal to delete wave from database

    class WaveColumnItem(ScopeOutWidget):
        """
        A rectangular box showing basic information about a captured waveform.
        Used to dynamically populate the waveColumnWidget.
        """

        wave_signal = QtCore.pyqtSignal(Waveform)
        save_signal = QtCore.pyqtSignal(Waveform)
        save_properties_signal = QtCore.pyqtSignal(Waveform)  # signal to pass wave to property saving routine
        delete_signal = QtCore.pyqtSignal(ScopeOutWidget)

        def __init__(self, parent, wave, *args):
            """
            constructor

            Parameters:
                :parent: the parent widget, should be waveColumnWidget
                :wave: the wave dictionary to be wrapped.
                :index: the index of the wave in the waveColumnWidget.
            """

            ScopeOutWidget.__init__(self, *args)

            self.logger = logging.getLogger('ScopeOut.widgets.waveColumnItem')
            self.parent = parent

            # Actions
            display_action = QtWidgets.QAction('Display Waveform', self)
            display_action.triggered.connect(self.display_wave)
            self.addAction(display_action)

            self.properties = None
            show_properties_action = QtWidgets.QAction('Display Properties', self)
            show_properties_action.triggered.connect(self.make_properties_popup)
            self.addAction(show_properties_action)

            separator = QtWidgets.QAction(self)
            separator.setSeparator(True)
            self.addAction(separator)

            self.save_action = QtWidgets.QAction('Save Waveform', self)
            self.save_action.triggered.connect(lambda: self.save_signal.emit(self.wave))
            self.addAction(self.save_action)

            save_properties_action = QtWidgets.QAction('Save Properties', self)
            save_properties_action.triggered.connect(lambda: self.save_properties_signal.emit(self.wave))
            self.addAction(save_properties_action)

            separator = QtWidgets.QAction(self)
            separator.setSeparator(True)
            self.addAction(separator)

            delete_action = QtWidgets.QAction('Delete Waveform', self)
            delete_action.triggered.connect(lambda: self.delete_signal.emit(self))
            self.addAction(delete_action)

            # Setup Widgets
            self.wave = wave
            time = str(wave.capture_time)
            display_time = self.make_display_time(time)
            self.wave_time = QtWidgets.QLabel(display_time, self)
            self.wave_id = QtWidgets.QLabel(str(wave.id), self)
            self.delete_button = QtWidgets.QPushButton('X', self)
            self.delete_button.clicked.connect(lambda: self.delete_signal.emit(self))

            # Layout
            self.layout = QtWidgets.QGridLayout(self)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(2)
            self.layout.addWidget(self.wave_id, 0, 0)
            self.layout.addWidget(self.wave_time, 0, 1)
            self.layout.setColumnMinimumWidth(0, 50)
            self.layout.setColumnMinimumWidth(1, 60)
            if self.peak_detected:
                self.layout.addWidget(QtWidgets.QLabel('^', self), 0, 2)
            self.layout.setColumnStretch(2, 1)
            self.layout.addWidget(self.delete_button, 0, 3)
            self.setLayout(self.layout)

        def make_display_time(self, datetime):
            """
            Converts the time of wave acquisiton into a tidier format for display.

            Parameters:
                :datetime: acquisition time string generated by DateTime
            """

            time, partial = datetime.split(' ')[-1].split('.')
            return '{}.{}'.format(time, partial[:2])

        def mousePressEvent(self, event):
            """
            Emits wave_signal on widget click, which should result in the wrapped wave being plotted.
            """

            if event.button() == QtCore.Qt.LeftButton:
                if self.property('state') != 'active' or not self.parent.hold:
                    self.display_wave()

        def display_wave(self):
            """
            Causes the wave to be displayed and updates the column to make this item active.
            Fetches the wave's y data if it is not loaded.
            """

            self.wave_signal.emit(self.wave)
            self.setProperty('state', 'active')
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

        def make_properties_popup(self):
            """
            Spawns properties popup window when activated.
            Makes new window if no cached version exists.
            """

            if self.properties is None:
                self.properties = self.PropertiesPopup(self.wave)
                self.properties.setGeometry(QtCore.QRect(100, 100, 400, 200))

            self.properties.show()

        @property
        def peak_detected(self):
            """
            Returns true if the wrapped peak has a detected wave, False otherwise
            """
            try:
                return self.wave.peak_start is not None and self.wave.peak_start > 0
            except:
                return False

        class PropertiesPopup(ScopeOutWidget):
            """
            Popup window to display wave properties.
            """

            def __init__(self, wave, *args):
                """
                Constructor.

                Parameters:
                    :wave: The Waveform whose properties are to be displayed.
                """

                ScopeOutWidget.__init__(self, *args)
                self.logger = logging.getLogger('ScopeOut.widgets.waveColumnItem.PropertiesPopup')

                self.setWindowTitle('Wave Properties')
                self.setStyleSheet('color: white; background-color: #3C3C3C;')

                layout = QtWidgets.QGridLayout(self)
                layout.addWidget(QtWidgets.QLabel('Wave Properties:', self), 0, 0)

                # Add base property readouts
                y = 1
                for key, value in sorted(wave.__dict__.items()):
                    if not isinstance(getattr(wave, key), list) and not key.startswith('_'):
                        label_text = key.title().replace('_', ' ')
                        label = QtWidgets.QLabel('  ' + label_text, self)
                        layout.addWidget(label, y, 0)
                        value = QtWidgets.QLabel('{}'.format(getattr(wave, key)), self)
                        layout.addWidget(value, y, 1)
                        y += 1

                # Added peak properties section
                layout.setRowMinimumHeight(y + 1, 10)
                layout.addWidget(QtWidgets.QLabel('Peak Properties:', self), y + 2, 0)
                if wave.peak_start < 0:
                    layout.addWidget(QtWidgets.QLabel('  No Peak Detected', self), y + 3, 0)
                else:
                    peak_start_string = str(wave.x_list[wave.peak_start]) + ' ' + str(wave.x_unit)
                    peak_end_string = str(wave.x_list[wave.peak_end]) + ' ' + str(wave.x_unit)
                    peak_width_string = "{} {}".format(
                        wave.peak_end - wave.peak_start, wave.x_unit)
                    layout.addWidget(QtWidgets.QLabel('  Peak Start', self), y + 3, 0)
                    layout.addWidget(QtWidgets.QLabel(peak_start_string, self), y + 3, 1)
                    layout.addWidget(QtWidgets.QLabel('  Peak End', self), y + 4, 0)
                    layout.addWidget(QtWidgets.QLabel(peak_end_string, self), y + 4, 1)
                    layout.addWidget(QtWidgets.QLabel('  Peak Width', self), y + 5, 0)
                    layout.addWidget(QtWidgets.QLabel(peak_width_string, self), y + 5, 1)

                self.setLayout(layout)

    def __init__(self, *args):
        """
        constructor
        """

        QtWidgets.QScrollArea.__init__(self, *args)

        self.hold = False  # Governs whether multiple waves can be active at once
        self.empty_label_showing = True

        self.logger = logging.getLogger('ScopeOut.widgets.waveColumnWidget')
        self.empty_label = QtWidgets.QLabel('No Waveforms Acquired', self)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.insertWidget(0, self.empty_label, 0, QtCore.Qt.AlignCenter)

        container = ScopeOutWidget(self)
        container.setLayout(self.layout)

        self.setWidget(container)
        self.setWidgetResizable(True)

        self.add_shadow()

        self.show()

    def add_item(self, item):
        """
        Add a waveColumnItem to the column and display it.
        :param item: the WaveColumnItem to add.
        """

        assert type(item) is self.WaveColumnItem

        if self.empty_label_showing:
            self.empty_label.hide()
            self.layout.takeAt(0)
            self.layout.addStretch(0)
            self.empty_label_showing = False

        self.reset_colors()
        item.setProperty('state', 'active')
        self.layout.insertWidget(0, item)
        self.show()

        item.wave_signal.connect(self.wave_signal)
        item.wave_signal.connect(self.reset_colors)
        item.save_signal.connect(self.save_signal)
        item.delete_signal.connect(self.delete_item)
        item.save_properties_signal.connect(self.save_properties_signal)

        self.logger.info('Added wave #' + str(item.wave.id) + ' to column')

    def add_wave(self, wave):
        """
        Receive a Waveform, package it as a waveColumnItem, and add it to the column.

        Parameters:
            :wave: a Waveform.
        """

        assert type(wave) is Waveform

        self.add_item(self.WaveColumnItem(self, wave))

    def delete_item(self, item):
        """
        Remove the given wave column item from the list

        Parameters:
            :item: the WaveColumnItem to delete.
        """

        assert type(item) is self.WaveColumnItem

        self.logger.info('Deleting waveform #' + str(item.wave.id))
        try:
            self.layout.removeWidget(item)
            item.hide()
        except Exception as e:
            self.logger.error(e)
        finally:
            self.logger.info('Deleted waveform #' + str(item.wave.id))
            self.delete_signal.emit(item.wave)

    def reset(self):
        """
        Clear all waves from the list
        """

        self.logger.info("Resetting Wave Column")
        while self.layout.count() > 0:
            try:
                item = self.layout.takeAt(0)
                if item.widget() is not None:
                    item.widget().hide()
            except Exception as e:
                self.logger.error(e)
                break

        self.empty_label.show()
        self.layout.insertWidget(0, self.empty_label, 0, QtCore.Qt.AlignCenter)
        self.empty_label_showing = True
        self.repaint()

    def reset_colors(self):
        """
        Turn all of the wave items back to the default color
        """
        if not self.hold:  # Only reset the column if we're not showing multiple plots
            for i in range(0, self.layout.count() - 1):
                w = self.layout.itemAt(i).widget()
                w.setProperty('state', 'inactive')
                w.style().unpolish(w)
                w.style().polish(w)
                w.update()

    def set_plot_hold(self, bool):
        """
        Sets the hold variable, which governs whether or not multiple waves can be active
        at once. Called by a signal from the check box in the acqControlWidget.

        Parameters:
            :bool: Boolean value for self.hold.
        """

        self.hold = bool


class WaveColumnHeader(ScopeOutWidget):

    def __init__(self, *args):

        ScopeOutWidget.__init__(self, *args)

        self.id_label = QtWidgets.QLabel('ID', self)
        self.time_label = QtWidgets.QLabel('Time', self)
        self.peak_label = QtWidgets.QLabel('Peak', self)

        self.layout = QtWidgets.QHBoxLayout(self)

        self.layout.addWidget(self.id_label)
        self.layout.addSpacing(30)
        self.layout.addWidget(self.time_label)
        self.layout.addSpacing(30)
        self.layout.addWidget(self.peak_label)
        self.layout.addStretch(1)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.add_shadow()
        self.show()


class SelectPropertiesDialog(QtWidgets.QDialog):
    """
    A Modal dialog for acquiring the fields in the waveform which the user desires to save.
    """

    property_signal = QtCore.pyqtSignal(list)

    def __init__(self, wave):
        """
        Constructor.
        :param wave: A Waveform, from which the available properties will be collected.
        """

        QtWidgets.QDialog.__init__(self)
        self.setWindowTitle('Select Properties to Save')
        # Have to do styling manually
        self.setStyleSheet(
            """
            QPushButton {
                border-radius: 2px;
                background-color: #673AB7;
                max-width: 100px;
                padding: 6px;
                height: 20px;
                color: white;
                font-weight: bold;
                margin-bottom: 4px;
            }
            QPushButton:hover {background-color: #5E35B1;}
            QPushButton:pressed {background-color: #512DA8;}
            QCheckBox {color: white;}
            QDialog {background-color: #3C3C3C;}
            """)

        layout = QtWidgets.QGridLayout(self)
        x, y = 0, 0
        self.checks = []
        wave_dict = sorted(wave.__dict__.items())
        for key, value in wave_dict:
            if not isinstance(getattr(wave, key), list) and not key.startswith('_'):
                check = QtWidgets.QCheckBox(key, self)
                self.checks.append(check)
                layout.addWidget(check, y, x)
                # if y == len(wave_dict) / 2:
                #     y_max = y
                #     y = 0
                #     x += 1
                # else:
                y += 1

        ok_button = QtWidgets.QPushButton('OK', self)
        ok_button.released.connect(self.accept)
        layout.addWidget(ok_button, y, 0, 1, 2)
        self.setLayout(layout)

    def accept(self):

        self.property_signal.emit([check.text() for check in self.checks if check.isChecked()])
        self.done(0)

    def paintEvent(self, pe):
        """
        allows stylesheet to be used for custom widget.
        """

        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        p = QtGui.QPainter(self)
        s = self.style()
        s.drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, p, self)


class HistogramOptionsWidget(ScopeOutWidget):
    """
    Displays options for manipulating the histogram display.
    """

    def __init__(self, *args):
        """
        Constructor.
        :return:
        """

        self.logger = logging.getLogger('ScopeOut.widgets.HistogramOptionsWidget')
        ScopeOutWidget.__init__(self, *args)

        self.property_label = QtWidgets.QLabel('Property to Histogram', self)
        self.property_selector = QtWidgets.QComboBox(self)
        self.property_selector.setEnabled(False)

        self.bin_number_label = QtWidgets.QLabel('Number of Bins', self)
        self.bin_number_selector = QtWidgets.QSpinBox(self)

        try:
            self.bin_number_selector.setValue(int(Config.get('Histogram', 'number_of_bins')))
        except:
            self.bin_number_selector.setValue(100)

        self.layout = QtWidgets.QGridLayout(self)
        self.layout.addWidget(self.property_label, 0, 1)
        self.layout.addWidget(self.property_selector, 0, 2)
        self.layout.addWidget(self.bin_number_label, 1, 1)
        self.layout.addWidget(self.bin_number_selector, 1, 2)
        self.layout.setRowStretch(3, 1)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(3, 1)

        self.setLayout(self.layout)

        self.show()

    def update_properties(self, waveform):
        """
        Update the list of available properties.
        :param waveform: a Waveform.
        """

        if not self.property_selector.count():
            assert isinstance(waveform, Waveform)
            wave_dict = sorted(waveform.__dict__.items())
            properties = [key.title().replace('_', ' ') for key, value in wave_dict
                          if not key.startswith('_')
                          and isinstance(value, (int, float))
                          and value is not None]

            self.property_selector.addItems(properties)

            try:
                default_property = Config.get('Histogram', 'default_property')
                property_index = self.property_selector.findText(default_property)
                if property_index >= 0:
                    self.property_selector.setCurrentIndex(property_index)
            except:
                pass

            self.property_selector.setEnabled(True)

    def reset(self):
        """
        Clear the list of properties and disable the widget.
        """

        self.property_selector.clear()
        self.property_selector.setEnabled(False)
