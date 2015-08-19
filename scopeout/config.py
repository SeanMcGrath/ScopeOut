"""
Get configuration from config file
"""

import os
import logging
from configparser import ConfigParser

REQUIRED_SECTIONS = ['Themes', 'Database', 'Logging', 'Export', 'Peak Detection', 'Histogram']


class ScopeOutConfig:
    """
    Reads and writes to ScopeOut's configuration files
    """

    logger = logging.getLogger('ScopeOut.config.ScopeOutConfig')

    @classmethod
    def get_configuration(cls):
        parser = ConfigParser()
        
        parser.read(['../config.cfg', './config.cfg', os.path.expanduser('~/.ScopeOut/config.cfg')])

        # Check to make sure config file has all required sections
        if not set(REQUIRED_SECTIONS).issubset(parser.sections()):
            return cls.create_new_config()

        return parser
    
    @classmethod
    def get(cls, section, option):
        parser = cls.get_configuration()
        return parser.get(section, option)

    @classmethod
    def create_new_config(cls):
        """
        Write a new configuration file with default values.
        """
        parser = ConfigParser()

        parser.add_section('Themes')
        parser.set('Themes', 'theme_dir', os.path.abspath('./themes'))

        parser.add_section('Database')
        parser.set('Database', 'database_dir', os.path.expanduser('~/.ScopeOut/data'))
        parser.set('Database', 'database_file', 'scopeout.db')

        parser.add_section('Logging')
        parser.set('Logging', 'log_dir', os.path.expanduser('~/.ScopeOut/logs'))
        parser.set('Logging', 'log_file', 'ScopeOut.log')

        parser.add_section('Export')
        parser.set('Export', 'plot_dir', os.path.expanduser('~/.ScopeOut/plots'))
        parser.set('Export', 'waveform_dir', os.path.expanduser('~/.ScopeOut/waveforms'))

        parser.add_section('Peak Detection')
        parser.set('Peak Detection', 'Detection_method', 'Hybrid')
        parser.set('Peak Detection', 'smart_start_threshold', '50')
        parser.set('Peak Detection', 'smart_end_threshold', '50')
        parser.set('Peak Detection', 'fixed_start_time', '10')
        parser.set('Peak Detection', 'fixed_start_unit', 'ns')
        parser.set('Peak Detection', 'fixed_width_time', '10')
        parser.set('Peak Detection', 'fixed_width_unit', 'ns')
        parser.set('Peak Detection', 'hybrid_start_threshold', '50')
        parser.set('Peak Detection', 'hybrid_width_time', '10')
        parser.set('Peak Detection', 'hybrid_width_unit', 'ns')

        parser.add_section('Histogram')
        parser.set('Histogram', 'default_property', 'peak_integral')
        parser.set('Histogram', 'number_of_bins', '50')

        if not os.path.exists(os.path.expanduser('~/.ScopeOut')):
            os.makedirs(os.path.expanduser('~/.ScopeOut'))
        with open(os.path.expanduser('~/.ScopeOut/config.cfg'), 'w+') as file:
            parser.write(file)

        cls.logger.info('Wrote new configuration file')
        return parser
