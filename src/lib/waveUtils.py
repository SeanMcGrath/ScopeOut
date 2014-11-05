"""
Wave Utilities
==================

Defines useful mathematical operations for wave dictionary objects.
"""

import logging, numpy as np

logger = logging.getLogger("waveUtils")

def findPeakEnds(wave, t1, t2):
	"""
	Finds and returns the time at which the wave peak begins, with
	sensitivity determined by threshold.

	Parameters:
		:wave: the dictionary containing the wave information.
		:threshold: the fractional increase in y value defined
					as the beginning of a wave.
	"""

	try:
		start = 0
		startIndex = 0
		y = wave['yData']
		for i in range(0,len(y)-10):
			if y[i] != 0.0:
				if abs((y[i+5]-y[i])/(y[i])) > t1:
					if y[i+5] != 0.0 and abs((y[i+10]-y[i+5])/(y[i+5])) > t1:
						startIndex = i
						break

		if startIndex != 0:
			for i in range(startIndex,len(y) - 10):
				if y[i] != 0.0 and abs((y[i+5]-y[i])/(y[i])) < t2:
					if y[i+5] != 0.0 and abs((y[i+10]-y[i+5])/(y[i+5])) < t2:
						return wave['xData'][startIndex], wave['xData'][i]

		return startIndex, len(y)
		
	except Exception as e:
		logger.error(e)
		return 0,0
