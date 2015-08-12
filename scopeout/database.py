"""
Handle connection to database and instantiation of tables.
"""

import os
import logging

from queue import Queue
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
        self.queue = Queue()

        self.create_tables()

    def create_tables(self):
        """
        Creates all the tables necessary to run the application.
        """

        models.ModelBase.metadata.create_all(self.engine)
        self.logger.info("Database tables created")

    def consume(self):
        """
        Handle the next sql request in the queue
        """

        if self.queue.qsize():
            try:
                session = self.session()
                session.add(self.queue.get())
                session.commit()
            except Exception as e:
                self.logger.error(e)
                session.rollback()

    def consume_all(self):
        """
        Handle all sql requests in the queue
        """

        try:
            session = self.session()
            while self.queue.qsize():
                session.add(self.queue.get())
            session.commit()
        except Exception as e:
            self.logger.error(e)
            session.rollback()

