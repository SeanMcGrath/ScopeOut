from PyQt5 import QtGui, QtCore, QtWidgets
import lib.scopeGui as sg, sys, signal

root = QtWidgets.QApplication(sys.argv)
GUI = sg.ThreadedClient()

signal.signal(signal.SIGINT, signal.SIG_DFL)
sys.exit(root.exec_())