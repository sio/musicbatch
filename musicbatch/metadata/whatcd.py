'''
Manage archive of What.CD API responses
'''

import os
import json
from contextlib import contextmanager
from datetime import datetime
from html import unescape

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    Query,
    sessionmaker,
)

from musicbatch.metadata import VARIOUS_ARTISTS



Base = declarative_base()



class WhatAPIResponse(Base):
    '''Individual records for each API response'''
    __tablename__ = 'responses'

    filename = Column(String)
    infohash = Column(String, primary_key=True, nullable=False)
    raw = Column(String, nullable=False)
    target = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    album = Column(String)
    artist = Column(String)
    year = Column(Integer)
    image_url = Column(String)
    format = Column(String)


    def __init__(self, filename=None):
        super().__init__()
        self._parsed = None
        if filename is not None:
            self.filename = filename
            with open(filename) as response:
                raw = response.read()
            self.raw = raw
            data = json.loads(raw)
            self._parsed = data
            self.infohash = data['torrent']['infoHash']
            self.target = unescape(data['torrent']['filePath'])
            self.timestamp = datetime.strptime(
                data['group']['time'],
                '%Y-%m-%d %H:%M:%S'
            )
            self.album = unescape(data['group']['name'])
            try:
                artists = [unescape(a['name']) for a in data['group']['musicInfo']['artists']]
                if len(artists) > 3:
                    self.artist = VARIOUS_ARTISTS
                else:
                    self.artist = ', '.join(artists)
            except (TypeError, KeyError):
                self.artist = None
            self.year = data['group']['year']
            self.image_url = data['group']['wikiImage']
            self.format = data['torrent']['format']


    @property
    def json(self):
        '''Parsed version of JSON response'''
        if not self._parsed:
            self._parsed = json.loads(self.raw)
        return self._parsed



class WhatAPIArchive:
    '''SQLite backend for the archive or API responses'''


    def __init__(self, filename=None):
        if filename is None:
            url = 'sqlite://'
        else:
            url = 'sqlite:///{}'.format(os.path.abspath(filename))
        self.db = create_engine(url)
        Base.metadata.create_all(self.db)
        self.sessionmaker = sessionmaker(bind=self.db)


    @contextmanager
    def session(self):
        '''Context manager for database sessions'''
        short_session = self.sessionmaker()
        try:
            yield short_session
            short_session.commit()
        except:
            short_session.rollback()
            raise
        finally:
            short_session.close()


    def load(self, directory):
        '''Load all JSON files from the given directory (non-recursive)'''
        with self.session() as session:
            for filename in os.listdir(directory):
                if os.path.splitext(filename)[1].lower() != '.json':
                    continue
                record = WhatAPIResponse(os.path.join(directory, filename))
                session.add(record)


    def search(self, **filters):
        '''Search for responses in the archive'''
        query = Query(WhatAPIResponse).filter_by(**filters)
        with self.session() as session:
            return query.with_session(session)
