"""
Model classes to be hold data and be mapped to database.
"""

import logging
import numpy as np

from sqlalchemy import *
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

ModelBase = declarative_base()


class Waveform(ModelBase):
    """
    Model for waveforms acquired by oscilloscopes.
    """

    __tablename__ = 'waveforms'
    logger = logging.getLogger('ScopeOut.models.Waveform')

    # Columns
    id = Column(Integer, primary_key=True)
    capture_time = Column(DateTime, nullable=False)
    error = Column(String)
    peak_detection_mode = Column(String)
    peak_start = Column(Integer)
    peak_end = Column(Integer)
    data_width = Column(Integer)
    bits_per_point = Column(Integer)
    encoding = Column(String)
    binary_format = Column(String)
    significant_bit = Column(String)
    number_of_points = Column(Integer)
    point_format = Column(String)
    x_increment = Column(Float)
    x_offset = Column(Float)
    x_zero = Column(Float)
    x_unit = Column(String)
    y_offset = Column(Float)
    y_zero = Column(Float)
    y_unit = Column(String)
    y_multiplier = Column(Float)
    data_channel = Column(String)
    integral = Column(Float)

    # Attributes to be accessed during runtime, not saved
    _y_list = []
    _x_list = []

    @property
    def x_list(self):
        """
        Get array of x values that matches the y values in the waveform, scaled properly.

        :return: the x array needed to plot a waveform.
        """
        if not self._x_list:
            self._x_list = list(np.arange(0, self.number_of_points * self.x_increment,
                         self.x_increment))
        return self._x_list

    @property
    def y_list(self):
        if not self._y_list:
            self._y_list = [point.y for point in self.wave_data]
        return self._y_list

    def find_peak_smart(self, thresholds):
        """
        Finds and returns the indices at which the wave peak begins and ends, with
        sensitivity determined by the thresholds.

        Parameters:
            :wave: the dictionary containing the wave information.
            :t1: the fractional increase in y value defined as the beginning of a wave.
            :t2: The threshold within which the value of the wave must remain for the peak to be considered over.

        :Returns: The index of the start of the peak (-1 if not found) and the index of the end of the peak (-1 if not found).
        """

        t1 = thresholds[0]
        t2 = thresholds[1]

        try:
            start_index = -1
            y = [point.y for point in self.wave_data] or self.y_list
            y_max = max(np.absolute(y))
            for i in range(0, len(y) - 250):
                within_tolerance = 0
                for j in range(1, 3):
                    if y[i + 50 * (j - 1)] != 0.0 and abs(y[i + 50 * (j - 1)]) > 0.05 * y_max and abs(
                                    (y[i + 50 * j] - y[i + 50 * (j - 1)]) / (y[i + 50 * (j - 1)])) > t1:
                        within_tolerance += 1
                        if within_tolerance == 2:
                            start_index = i
                            break
                    else:
                        break
                if start_index >= 0: break

            if start_index >= 0:
                for i in range(start_index, len(y) - 250):
                    within_tolerance = 0
                    for j in range(1, 6):
                        if y[i + 50 * (j - 1)] != 0.0 and abs(y[i + 50 * (j - 1)]) < 0.2 * y_max and abs(
                                        (y[i + 50 * j] - y[i + 50 * (j - 1)]) / (y[i + 50 * (j - 1)])) < t2:
                            within_tolerance += 1
                            if within_tolerance == 4:
                                self.peak_start = start_index
                                self.peak_end = i
                        else:
                            break

            self.peak_start = start_index
            self.peak_end = len(self.x_list) - 1

        except Exception as e:
            self.logger.error(e)
            self.peak_start = -1
            self.peak_end = -1

    def find_peak_fixed(self, parameters):
        """
        Determine the start and end index from the start time and fixed peak width

        Parameters:
            :parameters: an array containing the start index of the peak followed by the fixed width.

        :Returns: a tuple of the starting index of the peak and the ending index.
        """

        start = parameters[0]
        width = parameters[1]
        x_data = [point.x for point in self.wave_data] or self.x_list
        start_index = 0
        while x_data[start_index] < start and start_index < len(x_data):
            start_index += 1

        end_index = start_index + int(width / self.x_increment)

        self.peak_start = start_index
        self.peak_end = end_index

    def find_peak_hybrid(self, parameters):
        """
        Determine the peak start analytically, then use a fixed peak width to find the end.

        Parameters:
            :parameters: an array containing the start peak threshold followed by the fixed peak width.

        :Returns: a tuple of the starting index of the ending index.
        """

        t1 = parameters[0]
        width = parameters[1]

        try:
            start_index = -1
            y = [point.y for point in self.wave_data] or self.y_list
            y_max = max(np.absolute(y))
            for i in range(0, len(y) - 250):
                within_tolerance = 0
                for j in range(1, 3):
                    if y[i + 50 * (j - 1)] != 0.0 and abs(y[i + 50 * (j - 1)]) > 0.05 * y_max and abs(
                                    (y[i + 50 * j] - y[i + 50 * (j - 1)]) / (y[i + 50 * (j - 1)])) > t1:
                        within_tolerance += 1
                        if within_tolerance == 2:
                            start_index = i
                            break
                    else:
                        break
                if start_index >= 0:
                    break

        except Exception as e:
            self.logger.error(e)
            self.peak_start = -1
            self.peak_end = -1

        index_width = int(width / self.x_increment)

        if start_index > 0:
            self.peak_start = start_index
            self.peak_end = start_index + index_width
        else:
            self.peak_start = 0
            self.peak_end = index_width

    def integrate_peak(self):
        """
        Integrate numerically over a wave's peak window.

        Parameters:
            :wave: a wave dictionary.

        :Returns: the result of the integral, or 0 if no suitable integration window is found.
        """

        try:
            start = self.peak_start
            if start < 0:
                return 0
            else:
                end = self.peak_end
                incr = self.x_increment
                y = [point.y for point in self.wave_data] or self.y_list
                result = 0
                if end < 0:
                    for i in range(start, len(y)):
                        result += y[i] * incr

                else:
                    for i in range(start, end):
                        result += y[i] * incr

            self.integral = result

        except Exception as e:
            self.logger.error(e)
            self.integral = 0

    def detect_peak_and_integrate(self, detection_mode, detection_parameters):
        """
        Determine whether the wave has a peak given the specified mode.
        If it does, integrate it.
        :param detection_mode: a string specifying which detection mode to use:
            'Smart', 'Fixed', or 'Hybrid'
        :param detection_parameters: the thresholds/parameters appropriate to the
            detection method chosen.
        """

        assert self.x_list is not []
        assert self.y_list is not []

        if 'Smart' in detection_mode:
            self.find_peak_smart(detection_parameters)
        elif 'Fixed' in detection_mode:
            self.find_peak_fixed(detection_parameters)
        elif 'Hybrid' in detection_mode:
            self.find_peak_hybrid(detection_parameters)

        self.integrate_peak()


class DataPoint(ModelBase):

    __tablename__ = 'wave_data'

    id = Column(Integer, primary_key=True)
    x = Column(Float)
    y = Column(Float)
    wave_id = Column(Integer, ForeignKey('waveforms.id'))

    waveform = relationship("Waveform", backref=backref('wave_data', order_by=id))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        return self.x < other.x
