from PyQt5 import QtGui, QtCore, QtWidgets
import lib.scopeGui as sg, sys

root = QtWidgets.QApplication(sys.argv)
GUI = sg.ThreadedClient()
sys.exit(root.exec_())