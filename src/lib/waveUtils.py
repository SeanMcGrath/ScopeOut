"""
Wave Utilities
==================

Defines useful mathematical operations for wave dictionary objects.
"""

import logging, numpy as np

logger = logging.getLogger("waveUtils")

def findPeakStart(wave, threshold):
	"""
	Finds and returns the time at which the wave peak begins, with
	sensitivity determined by threshold.

	Parameters:
		:wave: the dictionary containing the wave information.
		:threshold: the fractional increase in y value defined
					as the beginning of a wave.
	"""

	try:
		x = wave['xData']
		y = wave['yData']
		for i in range(0,len(y)-10):
			if y[i] != 0.0:
				if abs((y[i+5]-y[i])/(y[i])) > threshold:
					if y[i+5] != 0.0 and abs((y[i+10]-y[i+5])/(y[i+5])) > threshold:
						return x[i+1]
		return 0
	except Exception as e:
		logger.error(e)

