from PyQt5 import QtGui, QtCore, QtWidgets
import lib.scopeGui as sg, sys, signal

root = QtWidgets.QApplication(sys.argv)
root.GUI = sg.ThreadedClient()
print('GUI')
signal.signal(signal.SIGINT, signal.SIG_DFL)
sys.exit(root.exec_())
print('Done')
