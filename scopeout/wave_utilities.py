"""
Wave Utilities
==================

Defines useful mathematical operations for wave dictionary objects.
"""

import logging, numpy as np

logger = logging.getLogger("waveUtils")


def smartFindPeakEnds(wave, thresholds):
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
        y = wave['yData']
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
                            return startIndex, i
                    else:
                        break

        return startIndex, -1

    except Exception as e:
        logger.error(e)
        return -1, -1


def fixedFindPeakEnds(wave, parameters):
    """
    Determine the start and end index from the start time and fixed peak width

    Parameters:
        :parameters: an array containing the start index of the peak followed by the fixed width.

    :Returns: a tuple of the starting index of the peak and the ending index.
    """

    start = parameters[0]
    width = parameters[1]
    xData = wave["xData"]
    startIndex = 0
    while xData[startIndex] < start and startIndex < len(xData):
        startIndex += 1

    endIndex = startIndex + int(width / wave["X Increment"])

    return startIndex, endIndex


def hybridFindPeakEnds(wave, parameters):
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
        y = wave['yData']
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
        logger.error(e)
        return -1, -1

    indexWidth = int(width / wave["X Increment"])

    if startIndex > 0:
        return startIndex, startIndex + indexWidth
    else:
        return 0, indexWidth


def integratePeak(wave):
    """
    Integrate numerically over a wave's peak window.

    Parameters:
        :wave: a wave dictionary.

    :Returns: the result of the integral, or 0 if no suitable integration window is found.
    """

    try:
        start = wave['Start of Peak']
        if start < 0:
            return 0
        else:
            end = wave['End of Peak']
            incr = wave['X Increment']
            y = wave['yData']
            result = 0
            if end < 0:
                for i in range(start, len(y)):
                    result += y[i] * incr

            else:
                for i in range(start, end):
                    result += y[i] * incr

        return result

    except Exception as e:
        logger.error(e)
        return 0
