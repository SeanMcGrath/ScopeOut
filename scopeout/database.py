"""
Handle connection to database and instantiation of tables.
"""

import os
import logging

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import *

from scopeout.config import ScopeOutConfig as Config
import scopeout.models as models


class ScopeOutDatabase:
    """
    Provides a connection point to the application database
    and handles table creation.
    """

    def __init__(self, database_path=None):
        """
        Instantiate the database engine and bind it to a session.
        :param database_path: a path to an old database file to connect to.
         if this is not supplies, a new file will be generated.
        """

        self.logger = logging.getLogger('ScopeOut.database.ScopeOutDatabase')
        self.engine = None
        self.session = None

        if not database_path:
            database_path = create_new_database_file(datetime.now().strftime('%m-%d-%H-%M'))

        self.bind_to_database_file(database_path)

        if not self.has_tables:
            self.create_tables()

        if not self.is_setup:
            raise RuntimeError('Database setup failed at ' + database_path)

    def bind_to_database_file(self, file):
        """
        Associate this database with a *.db file.
        :param file: the path to the *.db file.
        """

        self.logger.info('Binding to database file ' + str(file))
        self.engine = create_engine('sqlite:///' + file)
        self.session = sessionmaker(bind=self.engine)

        self.logger.info('Database file has tables: ' + str(self.engine.table_names()))

    @property
    def is_setup(self):
        return self.engine is not None and self.session is not None and self.has_tables

    @property
    def has_tables(self):
        existing_tables = set(self.engine.table_names())
        required_tables = set(models.ModelBase.metadata.tables.keys())
        return existing_tables == required_tables

    def create_tables(self):
        """
        Creates all the tables necessary to run the application.
        """

        models.ModelBase.metadata.create_all(self.engine)
        self.logger.info("Database tables created")

    def bulk_insert_data_points(self, data, wave_id):
        """
        Insert a large number of DataPoints associated with a wave into the database.
        Circumvent the ORM for speed.
        :param data: a list of (x,y) data tuples.
        :param wave_id: the id of the wave the data belongs to.
        """

        try:
            self.engine.execute(
                models.DataPoint.__table__.insert(),
                [{'x': x, 'y': y, 'wave_id': wave_id} for (x, y) in data]
            )
        except Exception as e:
            self.logger.error(e)


def create_new_database_file(identifier):
    """
    Create a new database file for a new data acquisition session.
    :param identifier: a unique identifier to be prepended to the default file name.
    :return: a path to the newly created file.
    """

    database_dir = Config.get('Database', 'database_dir')
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)

    if identifier:
        database_file = identifier + Config.get('Database', 'database_file')
    else:
        database_file = Config.get('Database', 'database_file')

    database_path = os.path.join(database_dir, database_file)
    open(database_path, 'w').close()
    return database_path
