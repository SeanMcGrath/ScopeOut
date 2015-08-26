import sys
from cx_Freeze import setup, Executable

build_exe_options = {"packages": ["sqlalchemy"]}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name='ScopeOut',
    version='0.1',
    packages=['scopeout'],
    scripts=['ScopeOut.py'],
    install_requires =['visa',
                      'sqlalchemy',
                      'numpy',
                      'pyparsing',
                      'matplotlib',
                      'python-dateutil'],
    url='https://github.com/SeanMcGrath/ScopeOut',
    license='MIT License',
    author='Sean McGrath',
    author_email='srmcgrat@umass.edu',
    description='Use digital oscilloscopes as advanced data-acquisition tools.',
    options={"build_exe": build_exe_options},
    executables=[Executable("Scopeout.py", base=base)]
)


