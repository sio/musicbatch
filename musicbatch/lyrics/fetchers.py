'''
Fetch lyrics from public collections
'''

import re
from urllib.parse import quote

from lxml import etree
from lxml.html import HtmlComment, iterlinks

from scrapehelper.fetch import BaseDataFetcher, DataFetcherError
from musicbatch.lyrics.cyrillic import transliterate



class BaseLyricsFetcher(BaseDataFetcher):
    '''Base class for all lyrics fetchers'''

    HOME = NotImplemented  # Home URL for the lyrics source
    NOT_FOUND = None
    regex = {
        'empty_line': re.compile(r'^\s+$', re.MULTILINE),
        'except-alphanum': re.compile(r'[^\w\d]'),
        'except-alphanum-space-hyphen': re.compile(r'[^\w\d\s-]'),
        'except-whitespace-hyphen': re.compile(r'[\s-]+'),
        'many_linebreaks': re.compile(r'\n\n+'),
        'the_end': re.compile(r'(.*)(?:,\s*|[^,]\s+)the\s*$', re.IGNORECASE),
        'the_start': re.compile(r'^\s*the\s+(.*)', re.IGNORECASE),
        'whitespace': re.compile(r'\s+', re.DOTALL),
    }


    def __repr__(self):
        return '<{cls}({url})>'.format(
            cls = self.__class__.__name__,
            url = self.HOME,
        )


    @classmethod
    def check(cls, lyrics):
        '''Validate lyrics'''
        if cls.regex['whitespace'].sub('', lyrics):
            return cls.cleanup(lyrics)
        else:
            return cls.NOT_FOUND


    @classmethod
    def cleanup(cls, lyrics):
        '''Clean up some formatting mishaps'''
        regex = cls.regex
        clean = regex['empty_line'].sub('', lyrics)
        clean = regex['many_linebreaks'].sub('\n\n', clean)
        return clean


    @classmethod
    def fix_the(cls, caption, position='start'):
        '''
        Fix location of the "The" in a given caption

        If "the" is present, it will be moved either to the start or to the end
        of line according to the value of `position`
        '''
        regex = cls.regex
        if position == 'start':
            return regex['the_end'].sub(r'The \1', caption)
        elif position == 'end':
            return regex['the_start'].sub(r'\1, the', caption)
        elif position is None:
            for key in ('the_start', 'the_end'):
                if regex[key].match(caption):
                    return regex[key].sub(r'\1', caption)
            return caption
        else:
            raise ValueError('invalid argument value: position={}'.format(position))



class LyricsWikiFetcher(BaseLyricsFetcher):
    '''Fetch lyrics from Lyrics Wiki'''

    HOME = 'http://lyrics.wikia.com'
    api = 'http://lyrics.wikia.com/api.php'
    marker = re.compile(r'^.*<lyrics>(.*)</lyrics>.*$', re.DOTALL|re.IGNORECASE)
    noise = re.compile(r"''+", re.DOTALL)

    def __call__(self, artist, title):
        api_response = self.get(self.api, params=dict(
            action = 'lyrics',
            func = 'getSong',
            fmt = 'xml',  # JSON output is malformed! Single quotes all over the place
            artist = self.fix_the(artist),
            song = title,
        ))

        overview = etree.fromstring(api_response.content)
        if not overview.xpath('page_id//text()') \
        or int(overview.xpath('isOnTakedownList//text()')[0]):
            return self.NOT_FOUND

        full_page_url = overview.xpath('url//text()')[0]
        html = self.parse_html(full_page_url, params=dict(action='edit'))
        wiki_text = html.xpath('//*[@id="wpTextbox1"]//text()')[0]
        lyrics = self.marker.sub(r'\1', wiki_text)
        lyrics = self.noise.sub('', lyrics).strip()
        return self.check(lyrics)



class MusixMatchFetcher(BaseLyricsFetcher):
    '''Fetch lyrics form musixmatch.com'''

    HOME = 'https://www.musixmatch.com'
    RATELIMIT_CALLS = 10  # more gentle than default
    url_pattern = 'https://www.musixmatch.com/lyrics/{artist}/{title}'
    prepare = re.compile(r'[^\w\d]+', re.IGNORECASE)

    def __call__(self, artist, title):
        artist = self.fix_the(artist)
        artist, title = map(
            lambda x: self.prepare.sub('-', x),
            (artist, title)
        )
        try:
            html = self.parse_html(self.url_pattern.format(artist=artist, title=title))
        except DataFetcherError:
            return self.NOT_FOUND
        paragraphs = html.xpath('//span[@class="lyrics__content__ok"]//text()') \
                  or html.xpath('//span[@class="lyrics__content__warning"]//text()')
        lyrics = '\n\n'.join(p.strip() for p in paragraphs)
        return self.check(lyrics)



class MetroLyricsFetcher(BaseLyricsFetcher):

    HOME = 'http://metrolyrics.com/'
    url_pattern = 'http://www.metrolyrics.com/printlyric/{title}-lyrics-{artist}.html'
    disallowed = BaseLyricsFetcher.regex['except-alphanum-space-hyphen']
    strike = BaseLyricsFetcher.regex['except-whitespace-hyphen']


    def clean_caption(self, caption):
        caption = self.disallowed.sub('', caption.lower())
        caption = self.strike.sub('-', caption)
        return caption


    def __call__(self, artist, title):
        artist = self.fix_the(artist)
        artist, title = map(
            self.clean_caption,
            (artist, title)
        )
        try:
            html = self.parse_html(self.url_pattern.format(artist=artist, title=title))
        except DataFetcherError:
            return self.NOT_FOUND
        paragraphs = html.xpath('//p[@class="verse"]')
        lyrics = '\n\n'.join(p.text_content().strip() for p in paragraphs)
        return self.check(lyrics)



class LyricsModeFetcher(BaseLyricsFetcher):

    HOME = 'https://www.lyricsmode.com'
    RATELIMIT_CALLS = 10  # more gentle than default
    url_pattern = 'https://www.lyricsmode.com/lyrics/{char}/{artist}/{title}.html'
    disallowed = BaseLyricsFetcher.regex['except-alphanum-space-hyphen']
    strike = BaseLyricsFetcher.regex['except-whitespace-hyphen']


    def clean_caption(self, caption):
        caption = caption.strip()
        caption = self.disallowed.sub('', caption.lower())
        caption = self.strike.sub('_', caption)
        return caption


    def __call__(self, artist, title):
        artist = self.fix_the(artist, position=None)
        artist, title = map(
            self.clean_caption,
            (artist, title)
        )
        try:
            int(artist[0])
            char = '0-9'
        except ValueError:
            char = artist[0]
        except IndexError:
            char = ''
        try:
            html = self.parse_html(self.url_pattern.format(
                artist=artist,
                title=title,
                char=char,
            ))
        except DataFetcherError:
            return self.NOT_FOUND
        paragraphs = html.xpath('//div[@id="lyrics_text"]')
        if not paragraphs:
            return self.NOT_FOUND
        container = paragraphs[0]
        for child in container:
            if child.tag == 'div':
                container.remove(child)
        lyrics = container.text_content().strip()
        return self.check(lyrics)



class LyricsWorldRuFetcher(BaseLyricsFetcher):
    '''
    Fetcher for russian songs. Rather slow, so we don't use it on latin track
    names
    '''

    HOME = 'https://lyricsworld.ru'
    artist_url = 'https://lyricsworld.ru/{artist}/P{num}.html'
    disallowed = BaseLyricsFetcher.regex['except-alphanum-space-hyphen']
    strike = BaseLyricsFetcher.regex['except-whitespace-hyphen']
    cyrillic = re.compile(r'.*[а-я].*', re.IGNORECASE)


    def clean_artist(self, artist):
        artist = transliterate(artist)
        artist = self.disallowed.sub('', artist.lower())
        artist = self.strike.sub('-', artist)
        return artist


    @classmethod
    def clean_title(cls, title):
        title = cls.regex['except-alphanum'].sub('', title)
        return title.lower().replace('ё', 'е')


    def is_cyrillic(self, *texts):
        return bool(self.cyrillic.match(''.join(texts)))


    def __call__(self, artist, title):
        if not self.is_cyrillic(artist, title):
            return self.NOT_FOUND  # This fetcher is slow. Don't use it for non-cyrillic titles
        artist = self.fix_the(artist, position=None)
        artist = self.clean_artist(artist)
        title = self.clean_title(title)

        page_number = 1
        while True:
            try:
                artist_page = self.parse_html(self.artist_url.format(
                    artist=artist,
                    num=page_number,
                ))
                page_number += 1
            except DataFetcherError:
                return self.NOT_FOUND
            tracks = artist_page.xpath('//table[@class="tracklist"]//a')
            song_url = None
            for track in tracks:
                if self.clean_title(track.text_content()) == title:
                    song_url = track.get('href')
                    break
            if not song_url:
                continue  # try next page
            try:
                song_page = self.parse_html(song_url)
            except DataFetcherError:
                return self.NOT_FOUND
            lyrics = song_page.xpath('//p[@id="songLyricsDiv"]')
            if lyrics:
                return self.check(lyrics[0].text_content().strip())



class AzLyricsFetcher(BaseLyricsFetcher):

    HOME = 'https://www.azlyrics.com/'
    url_pattern = 'https://www.azlyrics.com/lyrics/{artist}/{title}.html'
    disallowed = BaseLyricsFetcher.regex['except-alphanum']
    marker = 'Sorry about that.'


    def clean_caption(self, caption):
        caption = self.disallowed.sub('', caption.lower())
        return caption


    def __call__(self, artist, title):
        artist = self.fix_the(artist, position=None)
        artist, title = map(
            self.clean_caption,
            (artist, title)
        )
        try:
            html = self.parse_html(self.url_pattern.format(artist=artist, title=title))
        except DataFetcherError:
            return self.NOT_FOUND
        comments = (e for e in html.iter() if isinstance(e, HtmlComment))
        for comment in comments:
            if self.marker in comment.text:
                lyrics = comment.getparent()
                break
        else:
            return self.NOT_FOUND
        for element in lyrics:
            if element.tag == 'div':
                lyrics.remove(element)
        return self.check(lyrics.text_content().strip())



class SongTexteFetcher(BaseLyricsFetcher):
    # TODO: filter out "Leider kein Songtext vorhanden."

    HOME = 'https://www.songtexte.com'
    search_url = 'https://www.songtexte.com/search'
    simplify = LyricsWorldRuFetcher.clean_title

    def __call__(self, artist, title):
        artist = self.fix_the(artist)
        artist_simplified, title_simplified = map(self.simplify, (artist, title))
        try:
            search_page = self.parse_html(
                self.search_url,
                params={
                    'c': 'songs',
                    'q': ' '.join((artist, title)),
                }
            )
        except DataFetcherError:
            return self.NOT_FOUND
        songs = search_page.xpath('//div[@class="songResultTable"]//div')
        for song in songs:
            artist_cell = song.xpath('(.//span[@class="artist"])[1]')
            title_cell = song.xpath('(.//span[@class="song"])[1]')
            if artist_cell and title_cell \
            and self.simplify(artist_cell[0].text_content().lower().lstrip('von\n')) == artist_simplified \
            and self.simplify(title_cell[0].text_content())  == title_simplified:
                for _, attr, link, _ in iterlinks(title_cell[0]):
                    if attr == 'href':
                        break_marker = True
                        break
                if break_marker: break
        else:
            return self.NOT_FOUND
        try:
            song_page = self.parse_html(link)
        except DataFetcherError:
            return self.NOT_FOUND
        lyrics = song_page.xpath('(.//div[@id="lyrics"])[1]')
        if not lyrics:
            return self.NOT_FOUND
        else:
            lyrics = lyrics[0]
        for element in lyrics:
            if element.tag == 'div':
                lyrics.remove(element)
        return self.check(lyrics.text_content().strip())
