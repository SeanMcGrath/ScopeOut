"""
Wave Utilities
==================

Defines useful mathematical operations for wave dictionary objects.
"""

import logging, numpy as np

logger = logging.getLogger("waveUtils")

def smartFindPeakEnds(wave, t1, t2):
	"""
	Finds and returns the indices at which the wave peak begins and ends, with
	sensitivity determined by the thresholds.

	Parameters:
		:wave: the dictionary containing the wave information.
		:t1: the fractional increase in y value defined as the beginning of a wave.
		:t2: The threshold within which the valuen of the wave must remain for the peak to be considered over.
	
	:Returns: The index of the start of the peak (-1 if not found) and the index of the end of the peak (-1 if not found).
	"""

	try:
		startIndex = -1
		y = wave['yData']
		ymax = max(np.absolute(y))
		for i in range(0,len(y)-250):
			withinTolerance = 0
			for j in range(1,3):
				if y[i+50*(j-1)] != 0.0 and abs(y[i+50*(j-1)]) > 0.05*ymax and abs((y[i+50*j]-y[i+50*(j-1)])/(y[i+50*(j-1)])) > t1:
					withinTolerance += 1
					if withinTolerance == 2:
						startIndex = i
						break
				else: 
					break
			if startIndex >= 0: break

		if startIndex != 0:
			for i in range(startIndex,len(y) - 250): 
				withinTolerance = 0
				for j in range(1,6):
					if y[i+50*(j-1)] != 0.0 and abs(y[i+50*(j-1)]) < 0.2*ymax and  abs((y[i+50*j]-y[i+50*(j-1)])/(y[i+50*(j-1)])) < t2:
						withinTolerance += 1
						if withinTolerance == 4:
							return startIndex, i
					else:
						break
						

		return startIndex, -1

	except Exception as e:
		logger.error(e)
		return 0,0

def integratePeak(wave):
	"""
	Integrate numerically over a wave's peak window.
	"""

	try:
		start = wave['peakStart']
		if start < 0:
			return 0
		else:
			end = wave['peakEnd']
			incr = wave['xIncr']
			y = wave['yData']
			result = 0
			if end < 0:
				for i in range(start, len(y)):
					result += y[i]*incr

			else:
				for i in range(start, end):
					result += y[i]*incr

		return result

	except Exception as e:
		logger.error(e)
		return 0
