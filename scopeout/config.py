"""
Get configuration from config file
"""

import os
import logging
from configparser import ConfigParser

REQUIRED_SECTIONS = ['Themes', 'Database', 'Logging', 'Export']


class ScopeOutConfig:
    """
    Reads and writes to ScopeOut's configuration files
    """

    logger = logging.getLogger('ScopeOut.config.ScopeOutConfig')

    @classmethod
    def get_configuration(cls):
        parser = ConfigParser()
        
        parser.read(['../config.cfg', './config.cfg', os.path.expanduser('~/.ScopeOut/config.cfg')])

        # Check to make sure config file has all require sections
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
        :return:
        """
        parser = ConfigParser()

        parser.add_section('Themes')
        parser.set('Themes', 'theme_dir', os.path.abspath('../themes'))

        parser.add_section('Database')
        parser.set('Database', 'database_dir', os.path.abspath('../data'))
        parser.set('Database', 'database_file', 'scopeout.db')

        parser.add_section('Logging')
        parser.set('Logging', 'log_dir', os.path.abspath('../logs'))
        parser.set('Logging', 'log_file', 'ScopeOut.log')

        parser.add_section('Export')
        parser.set('Export', 'plot_dir', os.path.abspath('../plots'))
        parser.set('Export', 'waveform_dir', os.path.abspath('../waveforms'))

        with open(os.path.abspath('../config.cfg'), 'w+') as file:
            parser.write(file)

        cls.logger.info('Wrote new configuration file')
        return parser
