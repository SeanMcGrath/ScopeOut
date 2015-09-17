"""
Get configuration from config file
"""

import os
import logging
from configparser import ConfigParser

REQUIRED_SECTIONS = ['VISA',
                     'Themes',
                     'Database',
                     'Logging',
                     'Export',
                     'Peak Detection',
                     'Histogram',
                     'Acquisition Control',
                     'View']

TRUE_STRINGS = ['true', 't', '1']
logger = logging.getLogger('ScopeOut.config.ScopeOutConfig')


class ScopeOutConfig:
    """
    Reads and writes to ScopeOut's configuration files
    """

    @staticmethod
    def get(section, option):
        """
        Get the configuration string for a configuration seciton and option.
        :param section: The configuration section name.
        :param option: The configuration option name.
        :return: the string matching section and option.
        """
        parser = get_configuration()
        return parser.get(section, option)

    @staticmethod
    def get_bool(section, options):
        """
        Get a boolean value from the configuration.
        :param section: the desired config section.
        :param options: the desired config option.
        :return: the boolean value matching section and option.
        """
        return ScopeOutConfig.get(section, options).lower() in TRUE_STRINGS

    @staticmethod
    def set(cls, section, option):

        parser = get_configuration()
        parser.set(section, option)
        cls.write_parser(parser)

    @staticmethod
    def set_multiple(tuple_list):
        """
        set multiple config values and write to disk.
        :param tuple_list:  a list of tuples to set as (section, option, value)
        """

        parser = get_configuration()
        [parser.set(section, option, str(value)) for section, option, value in tuple_list]
        write_parser(parser)


def get_configuration():
    parser = ConfigParser()

    parser.read(['../config.cfg', './config.cfg', os.path.expanduser('~/.ScopeOut/config.cfg')])

    # Check to make sure config file has all required sections
    if not set(REQUIRED_SECTIONS).issubset(parser.sections()):
        return create_new_config()

    return parser


def create_new_config():
    """
    Write a new configuration file with default values.
    """
    parser = ConfigParser()

    parser.add_section('VISA')
    parser.set('VISA', 'library_path', '')

    parser.add_section('View')
    parser.set('View', 'show_plot', 'True')
    parser.set('View', 'show_histogram', 'True')

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
    parser.set('Peak Detection', 'fixed_start_unit', 'nS')
    parser.set('Peak Detection', 'fixed_width_time', '10')
    parser.set('Peak Detection', 'fixed_width_unit', 'nS')
    parser.set('Peak Detection', 'hybrid_start_threshold', '50')
    parser.set('Peak Detection', 'hybrid_width_time', '10')
    parser.set('Peak Detection', 'hybrid_width_unit', 'nS')
    parser.set('Peak Detection', 'voltage_threshold_start_edge', 'below')
    parser.set('Peak Detection', 'voltage_threshold_start_value', '0')
    parser.set('Peak Detection', 'voltage_threshold_start_unit', 'V')
    parser.set('Peak Detection', 'voltage_threshold_end_edge', 'above')
    parser.set('Peak Detection', 'voltage_threshold_end_value', '0')
    parser.set('Peak Detection', 'voltage_threshold_end_unit', 'V')

    parser.add_section('Histogram')
    parser.set('Histogram', 'default_property', 'peak_integral')
    parser.set('Histogram', 'number_of_bins', '50')

    parser.add_section('Acquisition Control')
    parser.set('Acquisition Control', 'hold_plot', 'false')
    parser.set('Acquisition Control', 'show_peak', 'true')
    parser.set('Acquisition Control', 'data_channel', '1')

    write_parser(parser)
    logger.info('Wrote new configuration file')
    return parser


def write_parser(parser):
    """
    Record a parser's settings to the config file.
    """

    if not os.path.exists(os.path.expanduser('~/.ScopeOut')):
        os.makedirs(os.path.expanduser('~/.ScopeOut'))
    with open(os.path.expanduser('~/.ScopeOut/config.cfg'), 'w+') as file:
        parser.write(file)
