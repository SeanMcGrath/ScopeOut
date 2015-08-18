ScopeOut
========

An open-source software package that enables standard digital oscilloscopes to be used as advanced data-acquisition and analysis tools. Provides facilities for easily connecting to, operating, and extracting data from USB-capable oscilloscopes.

Installation
============

To run ScopeOut from source, the packages enumerated in `requirements.txt` must be installed via pip or otherwise. PyQt5 is also required, which must be installed from binaries available [here](https://riverbankcomputing.com/software/pyqt/download5). Then simply run `python ScopeOut.py` to initialize the GUI.

To connect to an oscilloscope, the VISA USB drivers must also be installed. These are available for download from National Instruments.

Compiled Versions
=================

A standalone windows executable for ScopeOut is available. Linux binaries are in development.

Supported Hardware
==================

ScopeOut was developed specifically for the Tektronix 2024B oscilloscope, but most of its codebase is oscilloscope agnostic. In theory, it can support any USB-capable scope with the proper extensions to the `oscilloscopes` module.

License
=======

ScopeOut is distributed freely under the MIT license.

Contact
=======

ScopeOut is being developed primarily by Sean McGrath under the auspices of UMass Amherst Medium-Energy Nuclear Physics. For more information, visit [smcgrath.me](smcgrath.me).