"""
Model classes to be hold data and be mapped to database.
"""

import numpy as np

from sqlalchemy import *
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import scopeout.utilities

ModelBase = declarative_base()
# logger = scopeout.utilities.get_logger('scopeout.models.Waveform')


class Waveform(ModelBase):
    """
    Model for waveforms acquired by oscilloscopes.
    """

    __tablename__ = 'waveforms'

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

    def get_x_data(self):
        return list(map(lambda data: data.x, self.x_data))

    def get_y_data(self):
        return list(map(lambda data: data.y, self.y_data))

    def smartFindPeakEnds(self, thresholds):
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
            startIndex = -1
            y = self['yData']
            ymax = max(np.absolute(y))
            for i in range(0, len(y) - 250):
                withinTolerance = 0
                for j in range(1, 3):
                    if y[i + 50 * (j - 1)] != 0.0 and abs(y[i + 50 * (j - 1)]) > 0.05 * ymax and abs(
                                    (y[i + 50 * j] - y[i + 50 * (j - 1)]) / (y[i + 50 * (j - 1)])) > t1:
                        withinTolerance += 1
                        if withinTolerance == 2:
                            startIndex = i
                            break
                    else:
                        break
                if startIndex >= 0: break

            if startIndex >= 0:
                for i in range(startIndex, len(y) - 250):
                    withinTolerance = 0
                    for j in range(1, 6):
                        if y[i + 50 * (j - 1)] != 0.0 and abs(y[i + 50 * (j - 1)]) < 0.2 * ymax and abs(
                                        (y[i + 50 * j] - y[i + 50 * (j - 1)]) / (y[i + 50 * (j - 1)])) < t2:
                            withinTolerance += 1
                            if withinTolerance == 4:
                                self.peak_start = startIndex
                                self.peak_end = i
                        else:
                            break

            self.peak_start = startIndex
            self.peak_end = -1

        except Exception as e:
            # logger.error(e)
            self.peak_start = -1
            self.peak_end = -1

    def fixedFindPeakEnds(self, parameters):
        """
        Determine the start and end index from the start time and fixed peak width

        Parameters:
            :parameters: an array containing the start index of the peak followed by the fixed width.

        :Returns: a tuple of the starting index of the peak and the ending index.
        """

        start = parameters[0]
        width = parameters[1]
        xData = self.x_data
        startIndex = 0
        while xData[startIndex] < start and startIndex < len(xData):
            startIndex += 1

        endIndex = startIndex + int(width / self.x_increment)

        self.peak_start = startIndex
        self.peak_end = endIndex

    def hybridFindPeakEnds(self, parameters):
        """
        Determine the peak start analytically, then use a fixed peak width to find the end.

        Parameters:
            :parameters: an array containing the start peak threshold followed by the fixed peak width.

        :Returns: a tuple of the starting index of the ending index.
        """

        t1 = parameters[0]
        width = parameters[1]

        try:
            startIndex = -1
            y = self['yData']
            ymax = max(np.absolute(y))
            for i in range(0, len(y) - 250):
                withinTolerance = 0
                for j in range(1, 3):
                    if y[i + 50 * (j - 1)] != 0.0 and abs(y[i + 50 * (j - 1)]) > 0.05 * ymax and abs(
                                    (y[i + 50 * j] - y[i + 50 * (j - 1)]) / (y[i + 50 * (j - 1)])) > t1:
                        withinTolerance += 1
                        if withinTolerance == 2:
                            startIndex = i
                            break
                    else:
                        break
                if startIndex >= 0: break

        except Exception as e:
            # logger.error(e)
            self.peak_start = -1
            self.peak_end = -1

        indexWidth = int(width / self["X Increment"])

        if startIndex > 0:
            self.peak_start = startIndex
            self.peak_end = startIndex + indexWidth
        else:
            self.peak_start = 0
            self.peak_end = indexWidth

    def integratePeak(self):
        """
        Integrate numerically over a wave's peak window.

        Parameters:
            :wave: a wave dictionary.

        :Returns: the result of the integral, or 0 if no suitable integration window is found.
        """

        try:
            start = self['Start of Peak']
            if start < 0:
                return 0
            else:
                end = self['End of Peak']
                incr = self['X Increment']
                y = self['yData']
                result = 0
                if end < 0:
                    for i in range(start, len(y)):
                        result += y[i] * incr

                else:
                    for i in range(start, end):
                        result += y[i] * incr

            self.integral = result

        except Exception as e:
            # logger.error(e)
            self.integral = 0


class XData(ModelBase):
    """
    Class representing x-axis data associated with a waveform.
    """

    __tablename__ = 'x_data'

    id = Column(Integer, primary_key=True)
    x = Column(Float)
    wave_id = Column(Integer, ForeignKey('waveforms.id'))

    waveform = relationship("Waveform", backref=backref('x_data', order_by=id))

    def __eq__(self, other):
        return self.x == other.x

    def __lt__(self, other):
        return self.x < other.x


class YData(ModelBase):
    """
    Class representing x-axis data associated with a waveform.
    """

    __tablename__ = 'y_data'

    id = Column(Integer, primary_key=True)
    y = Column(Float)
    wave_id = Column(Integer, ForeignKey('waveforms.id'))

    waveform = relationship("Waveform", backref=backref('y_data', order_by=id))

    def __eq__(self, other):
        return self.y == other.y

    def __lt__(self, other):
        return self.y < other.y
