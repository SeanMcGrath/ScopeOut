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
from PyQt5 import QtWidgets, QtCore

from scopeout.utilities import ScopeFinder
from scopeout.models import *
from scopeout.config import ScopeOutConfig as Config
from scopeout.database import ScopeOutDatabase as Database
from scopeout.filesystem import WaveformCsvFile
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
        connected in the connect_signals method.

        The actions of GUI components that interact with scopes and their data occur in the "event"
        methods of this client.

        It is essential that the Qt "signaling" mechanism be used to interact between threads
        (The GUI is considered a thread independent of this client). Directly modifying the
        appearance or contents of a GUI widget can cause a program crash; instead, emit the data
        you wish to send as a signal which the widget will receive safely.
    """

    lock = threading.Lock()  # Lock for scope resource

    stop_flag = threading.Event()  # Event representing termination of program
    acquisition_stop_flag = threading.Event()  # Event representing termination of continuous acquisition
    channel_set_flag = threading.Event()  # Set when data channel has been successfully changed.
    wave_acquired_flag = threading.Event()  # Set during continuous acquisition when a waveform has been acquired.
    continuous_flag = threading.Event()  # Set while program is finding scopes continuously
    continuous_flag.set()

    status_change_signal = QtCore.pyqtSignal(str)  # Signal sent to GUI waveform counter.
    scope_change_signal = QtCore.pyqtSignal(object)  # Signal sent to change the active oscilloscope.
    new_wave_signal = QtCore.pyqtSignal(Waveform)
    wave_added_to_db_signal = QtCore.pyqtSignal(Waveform)

    def __init__(self, *args):
        """
        Constructor
        """
        QtWidgets.QApplication.__init__(self, *args)

        # create logger
        self.logger = logging.getLogger('ScopeOut.gui.ThreadedClient')
        self.logger.info("Threaded Client initialized")

        # save a reference to the app database.
        # all access to the database must occur in this thread.
        self.database = None
        self.db_session = None

        # start in single-channel acquisition mode by default.
        self.multi_channel_acquisition = False

        # Create widgets.
        self.acquisition_control = sw.AcquisitionControlWidget(None)
        self.plot = sw.WavePlotWidget()
        self.histogram = sw.HistogramPlotWidget()
        self.wave_options = sw.WaveOptionsTabWidget()
        self.wave_column = sw.WaveColumnWidget()
        self.histogram_options = sw.HistogramOptionsWidget()

        self.logger.info("All Widgets initialized")

        widgets = {
            'column': self.wave_column,
            'plot': self.plot,
            'acqControl': self.acquisition_control,
            'wave_options': self.wave_options,
            'hist_options': self.histogram_options,
            'hist': self.histogram
        }

        commands = {'end': self.close_event}

        # Create main window that holds widgets.
        self.main_window = sw.ScopeOutMainWindow(widgets, commands)

        # Connect the various signals that shuttle data between widgets/threads.
        self.connect_signals()

        # Show the GUI
        self.main_window.show()

        # Oscilloscope and scope finder
        self.scopes = []
        self.active_scope = None
        self.scope_finder = ScopeFinder()

        # Thread timers.
        self.check_scope_timer = threading.Timer(5.0, self.check_scope)
        self.find_scope_timer = threading.Timer(0.1, self.find_scope)
        self.find_scope_timer.start()

    # noinspection PyUnresolvedReferences
    def connect_signals(self):
        """
        Connects signals from subwidgets to appropriate slots.
        """

        # Client Signals
        self.status_change_signal.connect(self.main_window.status)
        self.scope_change_signal.connect(self.acquisition_control.set_active_oscilloscope)
        self.new_wave_signal.connect(self.plot_wave)
        self.new_wave_signal.connect(self.save_wave_to_db)
        self.new_wave_signal.connect(self.update_histogram)
        self.new_wave_signal.connect(self.histogram_options.update_properties)
        self.wave_added_to_db_signal.connect(self.wave_column.add_wave)

        # Acq Control Signals
        self.acquisition_control.acquire_button.clicked.connect(partial(self.acq_event, 'now'))
        self.acquisition_control.acquire_on_trigger_button.clicked.connect(partial(self.acq_event, 'trig'))
        self.acquisition_control.continuous_acquire_button.clicked.connect(partial(self.acq_event, 'cont'))
        self.acquisition_control.channel_combobox.currentIndexChanged.connect(self.set_channel)
        self.acquisition_control.autoset_button.clicked.connect(self.autoset_event)
        self.acquisition_control.stop_acquisition_button.clicked.connect(self.acquisition_stop_flag.set)
        self.acquisition_control.hold_plot_checkbox.toggled.connect(self.wave_column.set_plot_hold)

        #  Main window Signals
        self.main_window.reset_action.triggered.connect(self.reset)
        self.main_window.reset_action.triggered.connect(self.wave_column.reset)
        self.main_window.save_action.triggered.connect(self.save_wave_to_disk)
        self.main_window.save_properties_action.triggered.connect(self.save_properties_to_disk)
        self.main_window.save_plot_action.triggered.connect(self.save_plot_to_disk)
        self.main_window.load_session_action.triggered.connect(self.load_database)

        #  Wave Column Signals
        self.wave_column.wave_signal.connect(self.plot_wave)
        self.wave_column.save_signal.connect(self.save_wave_to_disk)
        self.wave_column.save_properties_signal.connect(self.save_properties_to_disk)
        self.wave_column.delete_signal.connect(self.delete_wave)
        self.wave_column.delete_signal.connect(self.wave_column.reset)

        # Histogram Options signals
        self.histogram_options.property_selector.currentIndexChanged.connect(self.update_histogram)

        self.logger.info("Signals connected")

    def save_wave_to_db(self, wave):
        """
        Save a wave and its data in the database.
        :param wave: a Waveform, with its data contained in the x_list and y_list attributes.
        :return:
        """

        self.db_session.add(wave)
        try:
            self.db_session.commit()
            self.logger.info("Saved waveform #" + str(wave.id) + " to the database")

            self.wave_added_to_db_signal.emit(wave)

            data = zip(wave.x_list, wave.y_list)
            self.database.bulk_insert_data_points(data, wave.id)

        except Exception as e:
            self.logger.error(e)
            self.db_session.rollback()

    def plot_wave(self, wave):
        """
        Send a wave to the plotting widget.
        :param self:
        :param wave: a Waveform, with its data contained in the x_list and y_list attributes.
        """

        self.plot.show_plot(wave, self.acquisition_control.plot_held(), self.acquisition_control.show_peak_window)

    def update_histogram(self):
        """
        Update the histogram widget if the app is in histogram mode.
        """

        wave_property = self.histogram_options.property_selector.currentText().lower().replace(' ', '_')
        if wave_property:
            histogram_list = [val for (val,) in self.db_session.query(getattr(Waveform, wave_property)).all()]
            self.histogram.show_histogram(histogram_list, self.histogram_options.bin_number_selector.value())
            self.histogram.set_title(wave_property)

    def acq_event(self, mode):
        """
        Executed to collect waveform data from scope.

        Parameters:
            :mode: A string defining the mode of acquisition: {'now' | 'trig' | 'cont'}
        """

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

                wave.detect_peak_and_integrate(
                    self.wave_options.peak_detection_mode, self.wave_options.peak_detection_parameters)

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

            self.channel_set_flag.clear()

            if self.active_scope is not None:
                self.update_status('Acquiring data...')

                if not self.multi_channel_acquisition:

                    self.logger.info("Single channel acquisition")

                    try:
                        self.lock.acquire()
                        self.active_scope.make_waveform()
                        wave = self.active_scope.next_waveform
                    except Exception as e:
                        self.logger.error(e)
                        wave = None
                    finally:
                        if self.lock.locked():
                            self.lock.release()

                    if wave is not None and (not self.stop_flag.isSet()):
                        process_wave(wave)
                    else:
                        self.update_status('Error on Waveform Acquisition')

                else:
                    self.logger.info("Multichannel acquisition")

                    self.plot.reset_plot()

                    for i in range(0, self.active_scope.numChannels):

                        try:
                            self.logger.info("Acquiring data from channel %d", i + 1)
                            self.set_channel(i)
                            self.channel_set_flag.wait()
                            self.lock.acquire()
                            self.active_scope.make_waveform()
                            self.lock.release()
                            wave = self.active_scope.next_waveform
                        except Exception as e:
                            self.logger.error(e)
                            wave = None
                        finally:
                            if self.lock.locked():
                                self.lock.release()

                        if wave is not None and (not self.stop_flag.isSet()):
                            process_wave(wave)
                        else:
                            self.update_status('Error on Waveform Acquisition')

                    self.update_status('Acquired all active channels.')
                    self.multi_channel_acquisition = True
                    self.main_window.update()

                enable_buttons(True)

        def acquire_on_trig_thread():
            """
            Waits for the scope to trigger, then acquires and stores waveforms in the same way as immAcq.
            """

            self.lock.acquire()
            trigger_state = self.active_scope.getTriggerStatus()

            while trigger_state != 'TRIGGER' and not self.stop_flag.isSet() and not self.acquisition_stop_flag.isSet():
                trigger_state = self.active_scope.getTriggerStatus()

            if not self.stop_flag.isSet() and not self.acquisition_stop_flag.isSet():
                try:
                    self.active_scope.make_waveform()
                    wave = self.active_scope.next_waveform
                except AttributeError:
                    wave = None
                finally:
                    self.wave_acquired_flag.set()
                    if self.lock.locked():
                        self.lock.release()

            if not self.stop_flag.isSet() and not self.acquisition_stop_flag.isSet():
                if wave is not None:
                    process_wave(wave)
            elif self.acquisition_stop_flag.isSet():
                self.update_status('Acquisition terminated')
                self.logger.info('Acquisition on trigger terminated.')
                if mode == 'trig':
                    self.acquisition_stop_flag.clear()
                self.wave_acquired_flag.set()  # have to set this for continuous acq to halt properly
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

            while not self.stop_flag.isSet() and not self.acquisition_stop_flag.isSet():
                self.wave_acquired_flag.wait()
                if not self.acquisition_stop_flag.isSet():
                    acqThread = threading.Thread(target=acquire_on_trig_thread)
                    acqThread.start()
                self.wave_acquired_flag.clear()

            self.acquisition_stop_flag.clear()
            self.update_status("Continuous Acquisiton Halted.")
            enable_buttons(True)
            self.check_scope_timer = threading.Timer(5.0, self.check_scope)
            self.check_scope_timer.start()

        def enable_buttons(bool):
            """
            Disables/enables buttons that should not be active during acquisition.

            Parameters:
                :bool: True to enable buttons, false to disable.
            """

            self.acquisition_control.enable_buttons(bool)

        self.acquisition_stop_flag.clear()

        if not self.database:
            self.database = Database()
            self.db_session = self.database.session()

        if mode == 'now':  # Single, Immediate acquisition
            enable_buttons(False)
            self.logger.info("Immediate acquisition Event")
            acquisition_thread = threading.Thread(target=immediate_acquisition_thread)
            acquisition_thread.start()

        elif mode == 'trig':  # Acquire on trigger
            enable_buttons(False)
            self.update_status("Waiting for trigger...")
            self.logger.info("Acquisition on trigger event")
            acquisition_thread = threading.Thread(target=acquire_on_trig_thread)
            acquisition_thread.start()

        elif mode == 'cont':  # Continuous Acquisition
            enable_buttons(False)
            self.check_scope_timer.cancel()
            self.logger.info('Continuous Acquisition Event')
            self.update_status("Acquiring Continuously...")
            self.wave_acquired_flag.set()
            acquisition_thread = threading.Thread(target=continuous_acquisition_thread)
            acquisition_thread.start()

    def find_scope(self):
        """
        Continually checks for connected scopes, until one is found, then begins periodic checking.
        """

        if not self.stop_flag.is_set():

            self.scopes = self.scope_finder.refresh().get_scopes()

            while not self.scopes:  # Check for scopes and connect if possible
                if self.stop_flag.isSet():
                    self.scopes = []
                    break
                self.lock.acquire()
                self.scopes = self.scope_finder.refresh().get_scopes()
                self.lock.release()

            if not self.stop_flag.isSet():  # Scope Found!
                self.active_scope = self.scopes[0]
                self.logger.info("Set active scope to %s", str(self.active_scope))
                self.scope_change_signal.emit(self.active_scope)
                self.update_status('Found ' + str(self.active_scope))
                self.main_window.setEnabled(True)
                self.check_scope_timer = threading.Timer(5.0, self.check_scope)
                self.check_scope_timer.start()

    def check_scope(self):
        """
        Periodically confirms that scopes are still connected.
        """
        if not self.stop_flag.isSet():
            self.lock.acquire()
            connected = self.scope_finder.check_scope(0)
            if self.lock.locked():
                self.lock.release()
            if not connected:
                self.scopes = []
                self.logger.info("Lost Connection to Oscilloscope(s)")
                self.update_status("Lost Connection to Oscilloscope(s)")
                self.main_window.setEnabled(False)
                self.check_scope_timer.cancel()
                self.find_scope_timer = threading.Timer(0.1, self.find_scope)
                self.find_scope_timer.start()
            elif not self.stop_flag.isSet():
                self.check_scope_timer = threading.Timer(5.0, self.check_scope)
                self.check_scope_timer.start()

    def close_event(self):
        """
        Executed on app close.
        """

        self.logger.info('Closing ScopeOut. \n')
        self.stop_flag.set()
        self.continuous_flag.clear()
        self.check_scope_timer.cancel()
        self.quit()

    def reset(self):
        """
        Called to reset waveform and plot.
        """

        self.plot.reset_plot()
        self.wave_column.reset()
        self.histogram.reset()
        self.histogram_options.reset()
        self.update_status('Data Reset.')

        self.db_session = None
        self.database = None

    def set_channel(self, channel):
        """
        Set data channel of active scope.

        Parameters:
            :channel: desired data channel
        """

        channels = self.acquisition_control.data_channels

        def channel_thread():

            try:
                self.lock.acquire()
                if self.acquisition_control.scope.setDataChannel(channels[channel]):
                    self.logger.info('Successfully set data channel %s', channels[channel])
                    self.update_status('Data channel set to ' + channels[channel])
                else:
                    self.logger.debug('Failed to set data channel set to ' + channels[channel])
                    self.update_status('Failed to set data channel ' + channels[channel])
            except Exception as e:
                self.logger.error(e)
            finally:
                try:
                    self.channel_set_flag.set()
                    if self.lock.locked():
                        self.lock.release()
                except Exception as e:
                    self.logger.error(e)

        self.channel_set_flag.clear()
        self.logger.info('Attempting to set data channel %s', channels[channel])
        self.acquisition_control.continuous_acquire_button.setEnabled(True)
        self.acquisition_control.acquire_on_trigger_button.setEnabled(True)

        if channel in range(0, self.acquisition_control.scope.numChannels):
            self.multi_channel_acquisition = False
            set_channel_thread = threading.Thread(target=channel_thread)
            set_channel_thread.start()
        elif channels[channel] == 'All':
            self.logger.info("Selected all data channels")
            self.update_status("Selected all data channels")
            self.multi_channel_acquisition = True
        elif channels[channel] == 'Math':
            self.logger.info("selected Math data channel")
            self.update_status("selected Math data channel")
            self.multi_channel_acquisition = False
            set_channel_thread = threading.Thread(target=channel_thread)
            set_channel_thread.start()
            # No triggering in math mode
            self.acquisition_control.continuous_acquire_button.setEnabled(False)
            self.acquisition_control.acquire_on_trigger_button.setEnabled(False)
            self.acquisition_control.stop_acquisition_button.setEnabled(False)

    def save_wave_to_disk(self, waveform=None):
        """
        Called in order to save in-memory waveforms to disk.

        Parameters:
            :wave: a particular wave to save, if none is passed then all waves in memory are saved.
        """

        if waveform:
            try:
                wave_directory = Config.get('Export', 'waveform_dir')
                if not os.path.exists(wave_directory):
                    os.makedirs(wave_directory)

                day_directory = os.path.join(wave_directory, date.today().isoformat())
                if not os.path.exists(day_directory):
                    os.makedirs(day_directory)

                default_file = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
                default_file = os.path.join(day_directory, default_file).replace('\\', '/')

                file_name = QtWidgets.QFileDialog.getSaveFileName(self.main_window, 'Save As', default_file)[0]

                with WaveformCsvFile(waveform, file_name) as file:
                    file.write()

                self.logger.info('Waveform saved to ' + file_name)
                self.update_status('Waveform saved to ' + file_name)

            except Exception as e:
                self.logger.error(e)

        else:
            wave_count = self.db_session.query(Waveform).count()
            if wave_count:
                try:
                    wave_directory = Config.get('Export', 'waveform_dir')
                    if not os.path.exists(wave_directory):
                        os.makedirs(wave_directory)

                    day_directory = os.path.join(wave_directory, date.today().isoformat())
                    if not os.path.exists(day_directory):
                        os.makedirs(day_directory)

                    default_file = 'Capture' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
                    default_file = os.path.join(day_directory, default_file).replace('\\', '/')

                    file_name = QtWidgets.QFileDialog.getSaveFileName(self.main_window, 'Save As', default_file)[0]

                    with WaveformCsvFile(self.db_session.query(Waveform), file_name) as file:
                        file.write()

                    self.logger.info("%d waveforms saved to %s", wave_count, file_name)
                    self.update_status('Waveforms saved to ' + file_name)

                except Exception as e:
                    self.logger.error(e)

            else:
                self.update_status('No Waveforms to Save')

    def save_properties_to_disk(self, waveform=None):
        """
        Save the values of any number of a waveform's properties to disk.

        Parameters:
            :waveform: a Waveform, the properties of which are to be saved.
                        If none is present, the properties of all waveforms in memory are saved.
        """

        def make_properties_file():
            wave_directory = Config.get('Export', 'waveform_dir')
            if not os.path.exists(wave_directory):
                os.makedirs(wave_directory)

            day_directory = os.path.join(wave_directory, date.today().isoformat())
            if not os.path.exists(day_directory):
                os.makedirs(day_directory)

            default_file = 'Properties' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.csv'
            default_file = os.path.join(day_directory, default_file).replace('\\', '/')

            file_name = QtWidgets.QFileDialog.getSaveFileName(self.main_window, 'Save As', default_file)[0]

            return file_name

        def write_properties(file_name, waves, fields):
            """
            Writes the selected properties of a list of Waveforms to a .csv file.

            Parameters:
                :file_name: the path to the output file.
                :waves: the list of Waveforms to be processed.
                :fields: an array containing the names of the selected properties.
            """

            try:
                with WaveformCsvFile(waves, file_name) as file:
                    file.write_properties(fields)

                self.logger.info('Waveform properties saved to ' + file_name)
                self.update_status('Waveform properties saved to ' + file_name)

            except Exception as e:
                self.logger.error(e)

        if waveform:
            properties_dialog = sw.SelectPropertiesDialog(waveform)
            properties_dialog.property_signal.connect(partial(write_properties, make_properties_file(), [waveform]))
            properties_dialog.exec()

        else:
            if self.db_session:
                wave_list = self.db_session.query(Waveform).all()
                properties_dialog = sw.SelectPropertiesDialog(wave_list[0])
                properties_dialog.property_signal.connect(partial(write_properties, make_properties_file(), wave_list))
                properties_dialog.exec()

            else:
                self.update_status('No waveforms to save.')

    def save_plot_to_disk(self):
        """
        Save the currently displayed plot to disk.
        """

        plot_directory = Config.get('Export', 'plot_dir')
        if not os.path.exists(plot_directory):
            os.makedirs(plot_directory)

        day_directory = os.path.join(plot_directory, date.today().isoformat())
        if not os.path.exists(day_directory):
            os.makedirs(day_directory)

        default_file = 'Plot' + datetime.now().strftime('%m-%d-%H-%M-%S') + '.png'
        default_file = os.path.join(day_directory, default_file).replace('\\', '/')

        file_name = QtWidgets.QFileDialog.getSaveFileName(self.main_window, 'Save As', default_file)[0]
        if self.plot.save_plot(file_name):
            self.update_status("Plot saved successfully")
        else:
            self.update_status("Error ")

    def update_status(self, message):
        """
        Print a message to the statusbar.

        Parameters:
            :message: The string to be printed.
        """

        self.status_change_signal.emit(message)

    def autoset_event(self):
        """
        Called when a scope autoset is requested.
        """

        def do_autoset():
            """
            Thread to execute the autoset.
            """

            self.lock.acquire()
            self.acquisition_control.scope.autoSet()
            self.lock.release()

        self.logger.info("Starting autoSet")
        self.update_status("Executing Auto-set. Ensure process is complete before continuing.")
        threading.Thread(target=do_autoset, name='AutoSetThread').start()

    def delete_wave(self, wave):
        """
        Removes the given waveform from the database.
        :param wave: the waveform to delete.
        """

        def delete_thread():

            self.db_session.delete(wave)
            self.db_session.commit()

        try:
            del_thread = threading.Thread(target=delete_thread)
            del_thread.start()
        except Exception as e:
            self.logger.error(e)

    def load_database(self):
        """
        Connect to an old database file, and load its waves into memory if it is valid.
        """

        try:
            default_file = Config.get('Database', 'database_dir')
            database_path = QtWidgets.QFileDialog.getOpenFileName(self.main_window, 'Open', default_file)[0]

            # Occurs if user hits cancel
            if database_path is '':
                return

            self.update_status('Loading waves from ' + database_path)
            self.logger.info('Disconnecting from database')

            # clear old session
            if self.db_session:
                self.db_session.close()
                self.db_session = None

            # reset GUI
            self.reset()

            self.update_status('Loading waves from ' + database_path)
            self.logger.info('Loading waves from ' + database_path)

            # make new connection
            self.database = Database(database_path)
            if self.database.is_setup:
                self.db_session = self.database.session()

            # get waves
            loaded_waves = self.db_session.query(Waveform).all()
            if not len(loaded_waves):
                raise RuntimeError('Database contained no waves.')

            # display waves to user.
            [self.wave_column.add_wave(wave) for wave in loaded_waves]
            try:
                self.plot.show_plot(loaded_waves[-1])
            except ValueError as e:
                self.logger.info(e)
            except Exception as e:
                self.logger.error(e)

            self.histogram_options.update_properties(loaded_waves[-1])
            self.update_histogram()
            self.update_status('Wave loading complete.')

        except Exception as e:
            self.logger.error(e)
            self.update_status('Failed to load waves from ' + database_path)

