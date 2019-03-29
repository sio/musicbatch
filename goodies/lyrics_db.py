'''
Scrape lyrics for all your songs into a database
'''


import os
import logging
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import (
    Query,
    sessionmaker,
)

from goodies.lyrics import (
    LyricsWikiFetcher,
    MusixMatchFetcher,
)



log = logging.getLogger(__name__)
Base = declarative_base()



class Lyrics(Base):
    __tablename__ = 'lyrics'

    artist = Column(String, primary_key=True)
    title = Column(String, primary_key=True)
    text = Column(String)
    source = Column(String)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )



class Schedule(Base):
    __tablename__ = 'schedule'

    artist = Column(String, primary_key=True)
    title = Column(String, primary_key=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )



class LyricsStorage:
    '''Persistent storage for song lyrics'''


    fetchers = (
        LyricsWikiFetcher(),
        MusixMatchFetcher(),
    )


    def __init__(self, filename=None):
        if filename is None:
            url = 'sqlite://'
        else:
            url = 'sqlite:///{}'.format(os.path.abspath(filename))
        self.db = create_engine(url)
        Base.metadata.create_all(self.db)
        self.sessionmaker = sessionmaker(bind=self.db)


    def get(self, artist, title):
        log.debug('Retrieving lyrics for: {} - {}'.format(artist, title))
        with self.session() as session:
            # 1. Return from storage
            query = Query(Lyrics).filter(
                (Lyrics.artist == artist),
                (Lyrics.title == title),
            )
            for lyrics in query.with_session(session):
                log.debug('Lyrics found in storage')
                return lyrics.text

            # 2. Use fetchers to retrieve lyrics
            schedule_query = Query(Schedule).filter(
                (Schedule.artist == artist),
                (Schedule.title == title),
            )
            for fetcher in self.fetchers:
                text = fetcher(artist, title)
                if text is fetcher.NOT_FOUND:
                    continue
                lyrics = Lyrics(artist=artist, title=title, text=text, source=fetcher.HOME)
                session.add(lyrics)
                schedule_query.with_session(session).delete()
                log.debug('Lyrics fetched from {}'.format(fetcher.HOME))
                return lyrics.text

            # 3. Record failure
            schedule = schedule_query.with_session(session).first()
            if not schedule:
                schedule = Schedule(artist=artist, title=title)
                session.add(schedule)
            else:
                schedule.timestamp = datetime.utcnow()
            log.debug('Lyrics not found. Scheduled for later')
            return fetcher.NOT_FOUND


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
