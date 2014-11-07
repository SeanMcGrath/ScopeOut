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
		:t1: the fractional increase in y value defined as the beginning of a wave.
	"""

	try:
		start = 0
		startIndex = 0
		y = wave['yData']
		ymax = max(np.absolute(y))
		for i in range(0,len(y)-250):
			withinTolerance = 0
			for j in range(1,6):
				if y[i+50*(j-1)] != 0.0 and abs(y[i+50*(j-1)]) > 0.05*ymax and abs((y[i+50*j]-y[i+50*(j-1)])/(y[i+50*(j-1)])) > t1:
					withinTolerance += 1
					if withinTolerance == 5:
						startIndex = i
						break
				else: 
					break
			if startIndex != 0: break

		if startIndex != 0:
			for i in range(startIndex,len(y) - 250): 
				withinTolerance = 0
				for j in range(1,6):
					if y[i+50*(j-1)] != 0.0 and abs(y[i+50*(j-1)]) < 0.2*ymax and  abs((y[i+50*j]-y[i+50*(j-1)])/(y[i+50*(j-1)])) < t2:
						withinTolerance += 1
						if withinTolerance == 4:
							return wave['xData'][startIndex], wave['xData'][i]
					else:
						break
						

		return wave['xData'][startIndex], wave['xData'][-10]

	except Exception as e:
		logger.error(e)
		return 0,0
