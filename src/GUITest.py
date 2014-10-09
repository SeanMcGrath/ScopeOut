from PyQt5 import QtGui, QtCore, QtWidgets
import lib.scopeGui as sg, sys, signal, os

def main():
	GUI = sg.ThreadedClient(sys.argv)
	GUI.mainWindow.show()
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	return GUI.exec_()

if __name__ == "__main__":
	sys.exit(main())

	