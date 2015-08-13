"""
Handle connection to database and instantiation of tables.
"""

import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import *

from scopeout.config import ScopeOutConfig as Config
import scopeout.models as models


class ScopeOutDatabase:
    """
    Provides a connection point to the application database
    and handles table creation.
    """

    def __init__(self):
        """
        Instantiate the database engine and bind it to a session.
        """

        self.logger = logging.getLogger('ScopeOut.database.ScopeOutDatabase')

        database_dir = Config.get('Database', 'database_dir')
        if not os.path.exists(database_dir):
            os.makedirs(database_dir)

        self.database_path = os.path.join(
            database_dir,
            Config.get('Database', 'database_file'))

        open(self.database_path, 'w').close()

        self.logger.info("Creating new database at " + self.database_path)
        self.engine = create_engine('sqlite:///' + self.database_path)
        self.session = scoped_session(sessionmaker(bind=self.engine))

        self.create_tables()

    def create_tables(self):
        """
        Creates all the tables necessary to run the application.
        """

        models.ModelBase.metadata.create_all(self.engine)
        self.logger.info("Database tables created")

    def bulk_insert_x(self, data, wave_id):
        """
        Insert a large number of XData points, circumventing the ORM for speed.
        :param data: a list of numeric x values.
        :param wave_id: the wave id to which the x values belong.
        """

        try:
            self.engine.execute(
                models.XData.__table__.insert(),
                [{'x': x, 'wave_id': wave_id} for x in data]
            )
        except Exception as e:
            self.logger.error(e)

    def bulk_insert_y(self, data, wave_id):
        """
        Insert a large number of YData points, circumventing the ORM for speed.
        :param data: a list of numeric y values.
        :param wave_id: the wave id to which the y values belong.
        """

        try:
            self.engine.execute(
                models.YData.__table__.insert(),
                [{'y': y, 'wave_id': wave_id} for y in data]
            )
        except Exception as e:
            self.logger.error(e)
