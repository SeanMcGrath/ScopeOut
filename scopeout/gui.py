"""
ScopeOut GUI

Defines GUI client that instantiates and controls widgets and threads.
"""

# Set matplotlib to call PyQt5
from matplotlib import rcParams
rcParams['backend'] = 'Qt5Agg'

import threading
import os
import logging

from datetime import date, datetime
from functools import partial
from PyQt5 import QtWidgets, QtCore, QtGui

from scopeout.utilities import ScopeFinder as sf
from scopeout.models import *
import scopeout.widgets as sw


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
        (The GUI is considered a thread independent of this client). Directly modifying the
        appearance or contents of a GUI widget can cause a program crash; instead, emit the data
        you wish to send as a signal which the widget will receive safely.
    """

    lock = threading.Lock()  # Lock for scope resource

    stopFlag = threading.Event()  # Event representing termination of program
    acqStopFlag = threading.Event()  # Event representing termination of continuous acquisition
    channelSetFlag = threading.Event()  # Set when data channel has been successfully changed.
    acquireFlag = threading.Event()  # Set during continuous acquisition when a waveform has been acquired.
    continuousFlag = threading.Event()  # Set while program is finding scopes continuously
    continuousFlag.set()

    statusChange = QtCore.pyqtSignal(str)  # Signal sent to GUI waveform counter.
    scopeChange = QtCore.pyqtSignal(object)  # Signal sent to change the active oscilloscope.
    new_wave_signal = QtCore.pyqtSignal(Waveform)
    wave_added_to_db_signal = QtCore.pyqtSignal(Waveform)

    def __init__(self, database, *args):
        """
        Constructor
        """
        QtWidgets.QApplication.__init__(self, *args)

        # create logger
        self.logger = logging.getLogger('ScopeOut.gui.ThreadedClient')
        self.logger.info("Threaded Client initialized")

        # save a reference to the app database.
        # all access to the database must occur in this thread.
        self.database = database

        # start in waveform display mode by default.
        self.histMode = False

        # Create widgets.
        self.acqControl = sw.acqControlWidget(None)
        self.plot = sw.WavePlotWidget()
        self.hist = sw.HistogramPlotWidget()
        self.waveOptions = sw.waveOptionsTabWidget()
        self.waveColumn = sw.WaveColumnWidget()

        self.logger.info("All Widgets initialized")

        widgets = {
            'column': self.waveColumn,
            'plot': self.plot,
            'acqControl': self.acqControl,
            'options': self.waveOptions,
            'hist': self.hist
        }
        commands = {'end': self.close_event}

        # Create main window that holds widgets.
        self.mainWindow = sw.ScopeOutMainWindow(widgets, commands)

        # Connect the various signals that shuttle data between widgets/threads.
        self.connect_signals()

        # Start looking for oscilloscopes.
        scope_finder_thread = threading.Thread(target=self.find_scope, name='ScopeFind')
        scope_finder_thread.start()

        # Show the GUI
        self.mainWindow.show()

    def connect_signals(self):
        """
        Connects signals from subwidgets to appropriate slots.
        """

        # Client Signals
        self.statusChange.connect(self.mainWindow.status)
        self.scopeChange.connect(self.acqControl.setScope)
        self.wave_added_to_db_signal.connect(self.waveColumn.addWave)
        self.new_wave_signal.connect(self.plot_wave)
        self.new_wave_signal.connect(self.save_wave_to_db)
        self.new_wave_signal.connect(self.update_histogram)

        # Acq Control Signals
        self.acqControl.acqButton.clicked.connect(partial(self.acq_event, 'now'))
        self.acqControl.acqOnTrigButton.clicked.connect(partial(self.acq_event, 'trig'))
        self.acqControl.contAcqButton.clicked.connect(partial(self.acq_event, 'cont'))
        self.acqControl.channelComboBox.currentIndexChanged.connect(self.set_channel)
        self.acqControl.autoSetButton.clicked.connect(self.autoset_event)
        self.acqControl.acqStopButton.clicked.connect(self.acqStopFlag.set)
        self.acqControl.holdPlotCheckBox.toggled.connect(self.waveColumn.setHold)

        #  Main window Signals
        self.mainWindow.resetAction.triggered.connect(self.reset_event)
        self.mainWindow.resetAction.triggered.connect(self.waveColumn.reset)
        self.mainWindow.saveAction.triggered.connect(self.save_wave_to_disk)
        self.mainWindow.savePropertiesAction.triggered.connect(self.save_properties_to_disk)
        self.mainWindow.savePlotAction.triggered.connect(self.save_plot_to_disk)

        #  Wave Column Signals
        self.waveColumn.waveSignal.connect(self.plot_wave)
        self.waveColumn.saveSignal.connect(self.save_wave_to_disk)
        self.waveColumn.savePropsSignal.connect(self.save_properties_to_disk)
        self.waveColumn.deleteSignal.connect(self.delete_wave)

        self.logger.info("Signals connected")

    def save_wave_to_db(self, wave):
        """
        Save a wave and its data in the database.
        :param wave: a Waveform, with its data contained in the x_list and y_list attributes.
        :return:
        """

        def save_data_to_db():
            self.database.bulk_insert_x(wave.x_list, wave.id)
            self.database.bulk_insert_y(wave.y_list, wave.id)
            self.logger.info("Saved data for waveform #" + str(wave.id) + " to the database")

        session = self.database.session()
        session.add(wave)
        session.commit()

        self.logger.info("Saved waveform #" + str(wave.id) + " to the database")

        data_thread = threading.Thread(target=save_data_to_db)
        data_thread.start()

        # self.wave_added_to_db_signal.emit(wave)
        self.waveColumn.addWave(wave)
        self.update_wave_count(session.query(Waveform).count())

    def plot_wave(self, wave):
        """
        Send a wave to the plotting widget.
        :param self:
        :param wave: a Waveform, with its data contained in the x_list and y_list attributes.
        """

        if not self.histogram_mode:
            self.plot.showPlot(wave, self.acqControl.plotHeld(), self.waveOptions.peakStart())

    def update_histogram(self):
        """
        Update the histogram widget if the app is in histogram mode.
        """

        if self.histogram_mode:

            session = self.database.session()
            histogram_list = [hist for (hist,) in session.query(Waveform.integral).all()]
            self.hist.showHist(histogram_list)

    def acq_event(self, mode):
        """
        Executed to collect waveform data from scope.

        Parameters:
            :mode: A string defining the mode of acquisition: {'now' | 'trig' | 'cont'}
        """

        def get_peak_detection_mode():
            """
            Determine the desired method of peak detection from the status of the tab options widget.
            """
            return self.waveOptions.getMode()

        def process_wave(wave):
            """
            Extract wave and data from tuple generated by oscilloscope.
            Run desired calculations on acquired wave and display plots.

            Parameters:
                :wave_tuple: a tuple containing a Waveform, a list of x values, and a list of y values.
            """

            try:
                assert type(wave) is Waveform

                if wave.error is not None:
                    self.logger.error("Wave error: %s", wave.error)
                    self.update_status(wave.error)
                    return

                wave.detect_peak_and_integrate(get_peak_detection_mode(), self.waveOptions.getParameters())

                self.logger.info("Successfully acquired waveform from %s", wave.data_channel)
                self.update_status('Waveform acquired on ' + wave.data_channel)

            except Exception as e:
                self.update_status('Error occurred during wave processing. Check log for details.')
                self.logger.error(e)
            finally:
                self.new_wave_signal.emit(wave)

        def immediate_acquisition_thread():
            """
            Contains instructions for acquiring and storing waveforms ASAP.
            self.multiAcq serves as the flag to initiate multi-channel acquisition.
            """

            self.channelSetFlag.clear()

            if self.activeScope is not None:
                self.update_status('Acquiring data...')

                if not self.multiAcq:

                    self.logger.info("Single channel acquisition")

                    try:
                        self.lock.acquire()
                        self.activeScope.makeWaveform()
                        wave = self.activeScope.getNextWaveform()
                    except Exception as e:
                        self.logger.error(e)
                        wave = None
                    finally:
                        if self.lock.locked():
                            self.lock.release()

                    if wave is not None and (not self.stopFlag.isSet()):
                        process_wave(wave)
                    else:
                        self.update_status('Error on Waveform Acquisition')

                else:
                    self.logger.info("Multichannel acquisition")

                    self.plot.resetPlot()

                    for i in range(0, self.activeScope.numChannels):

                        try:
                            self.logger.info("Acquiring data from channel %d", i + 1)
                            self.set_channel(i)
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
                            process_wave(wave)
                        else:
                            self.update_status('Error on Waveform Acquisition')

                    self.update_status('Acquired all active channels.')
                    self.multiAcq = True
                    self.mainWindow.update()

                enable_buttons(True)

        def acquire_on_trig_thread():
            """
            Waits for the scope to trigger, then acquires and stores waveforms in the same way as immAcq.
            """

            self.lock.acquire()
            trigger_state = self.activeScope.getTriggerStatus()

            while trigger_state != 'TRIGGER' and not self.stopFlag.isSet() and not self.acqStopFlag.isSet():
                trigger_state = self.activeScope.getTriggerStatus()

            if not self.stopFlag.isSet() and not self.acqStopFlag.isSet():
                try:
                    self.activeScope.makeWaveform()
                    wave = self.activeScope.getNextWaveform()
                except AttributeError:
                    wave = None
                finally:
                    self.acquireFlag.set()
                    if self.lock.locked():
                        self.lock.release()

            if not self.stopFlag.isSet() and not self.acqStopFlag.isSet():
                if wave is not None:
                    process_wave(wave)
            elif self.acqStopFlag.isSet():
                self.update_status('Acquisition terminated')
                self.logger.info('Acquistion on trigger terminated.')
                if mode == 'trig':
                    self.acqStopFlag.clear()
                self.acquireFlag.set()  # have to set this for continuous acq to halt properly
                if self.lock.locked():
                    self.lock.release()
            else:
                self.update_status('Error on Waveform Acquisition')
                self.logger.info('Error on Waveform Acquisition.')

            if mode == 'trig':
                enable_buttons(True)

        def continuous_acquisition_thread():
            """
            Continually runs trigAcqThread until the stop signal is received.
            """

            while not self.stopFlag.isSet() and not self.acqStopFlag.isSet():
                self.acquireFlag.wait()
                if not self.acqStopFlag.isSet():
                    acqThread = threading.Thread(target=acquire_on_trig_thread)
                    acqThread.start()
                self.acquireFlag.clear()

            self.acqStopFlag.clear()
            self.update_status("Continuous Acquisiton Halted.")
            enable_buttons(True)

        def enable_buttons(bool):
            """
            Disables/enables buttons that should not be active during acquisition.

            Parameters:
                :bool: True to enable buttons, false to disable.
            """

            self.acqControl.enableButtons(bool)

        self.acqStopFlag.clear()

        if mode == 'now':  # Single, Immediate acquisition
            enable_buttons(False)
            self.logger.info("Immediate acquisition Event")
            acqThread = threading.Thread(target=immediate_acquisition_thread)
            acqThread.start()

        elif mode == 'trig':  # Acquire on trigger
            enable_buttons(False)
            self.update_status("Waiting for trigger...")
            self.logger.info("Acquisition on trigger event")
            acqThread = threading.Thread(target=acquire_on_trig_thread)
            acqThread.start()

        elif mode == 'cont':  # Continuous Acquisiton
            enable_buttons(False)
            self.logger.info('Continuous Acquisition Event')
            self.update_status("Acquiring Continuously...")
            self.acquireFlag.set()
            acqThread = threading.Thread(target=continuous_acquisition_thread)
            acqThread.start()

    def find_scope(self):
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

                        self.scopes = self.finder.refresh().get_scopes()

                        while not self.scopes:  # Check for scopes and connect if possible
                            if self.stopFlag.isSet():
                                self.scopes = []
                                break
                            if not showedMessage:
                                self.update_status('No Oscilloscopes detected.')
                                showedMessage = True
                            self.lock.acquire()
                            self.scopes = self.finder.refresh().get_scopes()
                            self.lock.release()

                        if not self.stopFlag.isSet():  # Scope Found!
                            self.activeScope = self.scopes[0]
                            self.logger.info("Set active scope to %s", str(self.activeScope))
                            self.scopeChange.emit(self.activeScope)
                            self.update_status('Found ' + str(self.activeScope))
                            self.mainWindow.setEnabled(True)
                            self.continuousFlag.clear()
                            self.checkTimer = threading.Timer(5.0, self.check_scope)
                            self.checkTimer.start()

        self.logger.info("Scope acquisition thread ended")

    def check_scope(self):
        """
        Periodically confirms that scopes are still connected.
        """
        if not self.stopFlag.isSet():
            self.lock.acquire()
            connected = self.finder.check_scope(0)
            if self.lock.locked():
                self.lock.release()
            if not connected:
                self.scopes = []
                self.logger.info("Lost Connection to Oscilloscope(s)")
                self.update_status("Lost Connection to Oscilloscope(s)")
                self.mainWindow.setEnabled(False)
                self.continuousFlag.set()
                self.checkTimer.cancel()
            elif not self.stopFlag.isSet():
                self.checkTimer = threading.Timer(5.0, self.check_scope)
                self.checkTimer.start()

    def close_event(self):
        """
        Executed on app close.
        """

        self.logger.info('Closing ScopeOut. \n')
        self.stopFlag.set()
        self.continuousFlag.clear()
        self.checkTimer.cancel()
        self.quit()

    def reset_event(self):
        """
        Called to reset waveform and plot.
        """

        Waveform.query.delete()
        self.update_wave_count(0)
        self.plot.resetPlot()
        self.update_status('Data Reset.')

    def set_channel(self, channel):
        """
        Set data channel of active scope.

        Parameters:
            :channel: desired data channel
        """

        channels = self.acqControl.getChannels()

        def channel_thread():

            try:
                self.lock.acquire()
                if self.acqControl.scope.setDataChannel(channels[channel]):
                    self.logger.info('Successfully set data channel %s', channels[channel])
                    self.update_status('Data channel set to ' + channels[channel])
                else:
                    self.logger.debug('Failed to set data channel set to ' + channels[channel])
                    self.update_status('Failed to set data channel ' + channels[channel])
            except Exception as e:
                self.logger.error(e)
            finally:
                try:
                    self.channelSetFlag.set()
                    if self.lock.locked():
                        self.lock.release()
                except Exception as e:
                    self.logger.error(e)

        self.channelSetFlag.clear()
        self.logger.info('Attempting to set data channel %s', channels[channel])
        self.acqControl.contAcqButton.setEnabled(True)
        self.acqControl.acqOnTrigButton.setEnabled(True)

        if channel in range(0, self.acqControl.scope.numChannels):
            self.multiAcq = False
            setThread = threading.Thread(target=channel_thread)
            setThread.start()
        elif channels[channel] == 'All':
            self.logger.info("Selected all data channels")
            self.update_status("Selected all data channels")
            self.multiAcq = True
        elif channels[channel] == 'Math':
            self.logger.info("selected Math data channel")
            self.update_status("selected Math data channel")
            self.multiAcq = False
            setThread = threading.Thread(target=channel_thread)
            setThread.start()
            # No triggering in math mode
            self.acqControl.contAcqButton.setEnabled(False)
            self.acqControl.acqOnTrigButton.setEnabled(False)
            self.acqControl.acqStopButton.setEnabled(False)

    def save_wave_to_disk(self, waveform=None):
        """
        Called in order to save in-memory waveforms to disk.

        Parameters:
            :wave: a particular wave to save, if none is passed then all waves in memory are saved.
        """

        def write_wave(outFile, wave):
            """
            Write contents of waveform dictionary to .csv file.

            Parameters:
                :outFile: Open file object to be written to.
                :wave: full waveform dictionary.
            """

            try:
                outFile.write('"Waveform captured ' + str(wave.capture_time) + '"\n')
                outFile.write('\n')
                # for field in wave:
                #     if not isinstance(wave[field], (list, np.ndarray)):
                #         outFile.write('"' + field + '",' + str(wave[field]))
                #         outFile.write('\n')
                # outFile.write('\n')
                outFile.write('X,Y\n')
                for i in range(0, len(wave.x_data)):
                    try:
                        outFile.write(str(wave.x_data[i].x) + ',' + str(wave.y_data[i].y) + '\n')
                    except IndexError:
                        self.logger.error('X and Y data incompatible.')

                outFile.write('\n')

            except Exception as e:
                self.logger.error(e)

        if waveform:
            try:
                waveDirectory = os.path.join(os.getcwd(), 'waveforms')
                if not os.path.exists(waveDirectory):
                    os.makedirs(waveDirectory)

                dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
                if not os.path.exists(dayDirectory):
                    os.makedirs(dayDirectory)

                defaultFile = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
                defaultFile = os.path.join(dayDirectory, defaultFile).replace('\\', '/')

                fileName = QtWidgets.QFileDialog.getSaveFileName(self.mainWindow, 'Save As', defaultFile)[0]
                with open(fileName, 'w') as saveFile:
                    write_wave(saveFile, waveform)

                self.logger.info('Waveform saved to ' + fileName)
                self.update_status('Waveform saved to ' + fileName)

            except Exception as e:
                self.logger.error(e)

        else:
            session = self.database.session()
            wave_count = session.query(Waveform).count()
            if wave_count:
                try:
                    waveDirectory = os.path.join(os.getcwd(), 'waveforms')
                    if not os.path.exists(waveDirectory):
                        os.makedirs(waveDirectory)

                    dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
                    if not os.path.exists(dayDirectory):
                        os.makedirs(dayDirectory)

                    defaultFile = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
                    defaultFile = os.path.join(dayDirectory, defaultFile).replace('\\', '/')

                    fileName = QtWidgets.QFileDialog.getSaveFileName(self.mainWindow, 'Save As', defaultFile)[0]
                    with open(fileName, 'w') as saveFile:
                        for wave in session.query(Waveform):
                            write_wave(saveFile, wave)

                    self.logger.info("%d waveforms saved to %s", wave_count, fileName)
                    self.update_status('Waveforms saved to ' + fileName)

                except Exception as e:
                    self.logger.error(e)

            else:
                self.update_status('No Waveforms to Save')

    def save_properties_to_disk(self, waveform=None):
        """
        Save the values of any number of a waveform's properties to disk.

        Parameters:
            :waveform: a waveform dictionary, the properties of which are to be saved.
                        If none is present, the properties of all waveforms in memory are saved.
        """

        class SelectPropertiesPopup(QtWidgets.QDialog):
            """
            A Modal dialog for acquiring the fields in the waveform which the user desires to save.
            """

            def __init__(self, callback, waveform={}):
                """
                Constructor.

                Parameters:
                    :callback: a function to be executed on successful dialog close.
                                is passed the selected field names as an array.
                    :waveform: A waveform dictionary, from which the available field names are pulled.
                """

                self.callback = callback
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
                for field in waveform:
                    check = QtWidgets.QCheckBox(field, self)
                    self.checks.append(check)
                    layout.addWidget(check, y, x)
                    if y == len(waveform) / 2:
                        maxY = y
                        y = 0
                        x += 1
                    else:
                        y += 1

                okButton = QtWidgets.QPushButton('OK', self)
                okButton.released.connect(self.accept)
                layout.addWidget(okButton, maxY, 0, 1, 2)
                self.setLayout(layout)

            def accept(self):

                fields = [check.text() for check in self.checks if check.isChecked()]
                self.callback(fields=fields)
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

        def write_properties(outFile, waves, fields=[]):
            """
            Writes the selected properties of a waveform dictionary to a .csv file.

            Parameters:
                :outFile: an opened file object to be written to.
                :waves: the list of waveform dictionaries to be processed.
                :fields: an array containing the names of the selected properties.
            """

            try:
                outFile.write("Waveform properties captured {} \n\n".format(str(datetime.now())))
                for field in fields: outFile.write(field + ',')
                outFile.write('\n')
                for wave in waves:
                    for field in fields: outFile.write(str(wave[field]) + ',')
                    outFile.write('\n')

            except Exception as e:
                self.logger.error(e)

        if waveform:
            try:
                waveDirectory = os.path.join(os.getcwd(), 'waveforms')
                if not os.path.exists(waveDirectory):
                    os.makedirs(waveDirectory)

                dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
                if not os.path.exists(dayDirectory):
                    os.makedirs(dayDirectory)

                defaultFile = 'Properties' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
                defaultFile = os.path.join(dayDirectory, defaultFile).replace('\\', '/')

                fileName = QtWidgets.QFileDialog.getSaveFileName(self.mainWindow, 'Save As', defaultFile)[0]
                with open(fileName, 'w') as saveFile:
                    SelectPropertiesPopup(partial(
                        write_properties, outFile=saveFile, waves=[waveform]), waveform).exec()

                self.logger.info('Waveform properties saved to ' + fileName)
                self.update_status('Waveform properties saved to ' + fileName)

            except Exception as e:
                self.logger.error(e)

        else:
            session = self.database.session()
            wave_count = session.query(Waveform).count()
            if wave_count:
                try:
                    waveDirectory = os.path.join(os.getcwd(), 'waveforms')
                    if not os.path.exists(waveDirectory):
                        os.makedirs(waveDirectory)

                    dayDirectory = os.path.join(waveDirectory, date.today().isoformat())
                    if not os.path.exists(dayDirectory):
                        os.makedirs(dayDirectory)

                    defaultFile = 'Properties' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
                    defaultFile = os.path.join(dayDirectory, defaultFile).replace('\\', '/')

                    fileName = QtWidgets.QFileDialog.getSaveFileName(self.mainWindow, 'Save As', defaultFile)[0]
                    with open(fileName, 'w') as saveFile:
                        SelectPropertiesPopup(partial(
                            write_properties, outFile=saveFile, waves=self.waveList), self.waveList[0]).exec()

                    self.logger.info("Properties of %d waveforms saved to %s", len(self.waveList), fileName)
                    self.update_status("Properties of {} waveforms saved to {}".format(len(self.waveList), fileName))

                except Exception as e:
                    self.logger.error(e)

            else:
                self.update_status('No waveforms to save.')

    def save_plot_to_disk(self):
        """
        Save the currently displayed plot to disk.
        """

        if not self.waveList:
            self.update_status('No plot to save.')

        else:
            plotDirectory = os.path.join(os.getcwd(), 'plots')
            if not os.path.exists(plotDirectory):
                os.makedirs(plotDirectory)

            dayDirectory = os.path.join(plotDirectory, date.today().isoformat())
            if not os.path.exists(dayDirectory):
                os.makedirs(dayDirectory)

            defaultFile = 'Plot' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.png'
            defaultFile = os.path.join(dayDirectory, defaultFile).replace('\\', '/')

            fileName = QtWidgets.QFileDialog.getSaveFileName(self.mainWindow, 'Save As', defaultFile)[0]
            if self.plot.savePlot(fileName):
                self.update_status("Plot saved successfully")
            else:
                self.update_status("Error ")

    def update_status(self, message):
        """
        Print a message to the statusbar.

        Parameters:
            :message: The string to be printed.
        """

        self.statusChange.emit(message)

    def autoset_event(self):
        """
        Called when a scope autoset is requested.
        """

        def do_autoset():
            """
            Thread to execute the autoset.
            """

            self.lock.acquire()
            self.acqControl.scope.autoSet()
            self.lock.release()

        self.logger.info("Starting autoSet")
        self.update_status("Executing Auto-set. Ensure process is complete before continuing.")
        threading.Thread(target=do_autoset, name='AutoSetThread').start()

    def update_wave_count(self, waves):
        """
        Updates the counter displaying the total number of acquired waveforms.
        """

        self.waveOptions.updateCount(waves)

    @property
    def histogram_mode(self):
        """
        Check whether to display histogram or wave plot.
        """

        return self.mainWindow.histogramModeAction.isChecked()

    def delete_wave(self, wave):
        """
        Removes the given waveform from the database.
        :param wave: the waveform to delete.
        """
        try:
            session = self.database.session()
            session.delete(wave)
            session.commit()
            self.update_wave_count(session.query(Waveform).count())

        except Exception as e:
            self.logger.error(e)
