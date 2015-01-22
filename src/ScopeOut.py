from PyQt5 import QtGui, QtCore, QtWidgets
import lib.scopeGui as sg, sys, signal, os, logging

"""
ScopeOut
"""

import signal, threading, sys

def main():

	# create logger
	logger = logging.getLogger('ScopeOut')
	logger.setLevel(logging.DEBUG)
	# create file handler which logs even debug messages
	fh = logging.FileHandler('ScopeOut.log')
	fh.setLevel(logging.DEBUG)
	# create console handler with a higher log level
	ch = logging.StreamHandler()
	ch.setLevel(logging.ERROR)
	# create formatter and add it to the handlers
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)
	# add the handlers to the logger
	logger.addHandler(fh)
	logger.addHandler(ch)

	print("Initializing ScopeOut...")
	logger.info("Initializing ScopeOut...")
	GUI = sg.ThreadedClient(sys.argv)
	logger.info("ScopeOut initialization completed")
	# Enable keyboard shortcuts to kill from command line
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	return GUI.exec_()

if __name__ == "__main__":
	sys.exit(main())