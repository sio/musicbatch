'''
Scrape lyrics for all your songs into a database
'''


import os
import logging
from datetime import datetime
from contextlib import contextmanager

import mutagen
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

from transcoder.util import find_music
from transcoder.progress import ThreadSafeCounter
from transcoder.queue import execute_in_threadqueue
from goodies.lyrics import (
    LyricsModeFetcher,
    LyricsWikiFetcher,
    MetroLyricsFetcher,
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
        MetroLyricsFetcher(),
        LyricsModeFetcher(),
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
        self.stats = StorageStats()


    def get(self, artist, title):
        log.debug('Retrieving lyrics for: {} - {}'.format(artist, title))
        with self.session() as session:
            # 1. Return from storage
            query = Query(Lyrics).filter(
                (func.lower(Lyrics.artist) == func.lower(artist)),
                (func.lower(Lyrics.title) == func.lower(title)),
            )
            for lyrics in query.with_session(session):
                log.debug('Lyrics found in storage')
                self.stats.cached.increment()
                return lyrics.text

            # 2. Use fetchers to retrieve lyrics
            schedule_query = Query(Schedule).filter(
                (func.lower(Schedule.artist) == func.lower(artist)),
                (func.lower(Schedule.title) == func.lower(title)),
            )
            for fetcher in self.fetchers:
                text = fetcher(artist, title)
                if text is fetcher.NOT_FOUND:
                    continue
                lyrics = Lyrics(artist=artist, title=title, text=text, source=fetcher.HOME)
                session.add(lyrics)
                schedule_query.with_session(session).delete(synchronize_session=False)
                log.debug('Lyrics fetched from {}'.format(fetcher.HOME))
                self.stats.fetched.increment()
                return lyrics.text

            # 3. Record failure
            schedule = schedule_query.with_session(session).first()
            if not schedule:
                schedule = Schedule(artist=artist, title=title)
                session.add(schedule)
            else:
                schedule.timestamp = datetime.utcnow()
            log.debug('Lyrics not found. Scheduled for later')
            self.stats.missing.increment()
            return fetcher.NOT_FOUND


    def build_library(self, *directories):
        '''Build the library of lyrics for all songs in provided directories'''
        def songs():
            for filename in find_music(directories):
                tags = mutagen.File(filename, easy=True).tags
                artist = tags.get('artist')
                title = tags.get('title')
                if artist and title:
                    yield artist[0], title[0]
        execute_in_threadqueue(
            lambda args: self.get(*args),
            songs(),
            num_threads=os.cpu_count() * 3
        )


    def get_scheduled(self):
        '''Try to retrieve all scheduled songs'''
        with self.session() as session:
            query = Query((Schedule.artist, Schedule.title))
            songs = query.with_session(session)
            execute_in_threadqueue(
                lambda args: self.get(*args),
                songs,
                num_threads=os.cpu_count() * 3
            )


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



class StorageStats:
    '''Statistics of the current LyricsStorage session'''


    def __init__(self):
        self.reset()


    def reset(self):
        self.cached = ThreadSafeCounter()
        self.fetched = ThreadSafeCounter()
        self.missing = ThreadSafeCounter()


    def __str__(self):
        template = '{new} lyrics fetched, {missing} not found, {cached} from cache'
        return template.format(
            new = self.fetched,
            missing = self.missing,
            cached = self.cached,
        )


    def __format__(self, *a, **ka):
        return str(self).__format__(*a, **ka)
