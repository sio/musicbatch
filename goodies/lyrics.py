'''
Fetch lyrics from public collections
'''

import re
from urllib.parse import quote

from lxml import etree
from requests.exceptions import HTTPError

from api.fetch import BaseDataFetcher



class BaseLyricsFetcher(BaseDataFetcher):
    '''Base class for all lyrics fetchers'''

    HOME = NotImplemented  # Home URL for the lyrics source
    NOT_FOUND = None
    regex = {
        'the_start': re.compile(r'^\s*the\s+(.*)', re.IGNORECASE),
        'the_end': re.compile(r'(.*)(?:,\s*|[^,]\s+)the\s*$', re.IGNORECASE),
        'whitespace': re.compile(r'\s+', re.DOTALL),
        'empty_line': re.compile(r'^\s+$', re.MULTILINE),
        'many_linebreaks': re.compile(r'\n\n+'),
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
        except HTTPError:
            return self.NOT_FOUND
        paragraphs = html.xpath('//span[@class="lyrics__content__ok"]//text()') \
                  or html.xpath('//span[@class="lyrics__content__warning"]//text()')
        lyrics = '\n\n'.join(p.strip() for p in paragraphs)
        return self.check(lyrics)



class MetroLyricsFetcher(BaseLyricsFetcher):

    HOME = 'http://metrolyrics.com/'
    url_pattern = 'http://www.metrolyrics.com/printlyric/{title}-lyrics-{artist}.html'
    disallowed = re.compile(r'[^\w\d\s-]')
    strike = re.compile(r'[\s-]+')


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
        except HTTPError:
            return self.NOT_FOUND
        paragraphs = html.xpath('//p[@class="verse"]')
        lyrics = '\n\n'.join(p.text_content().strip() for p in paragraphs)
        return self.check(lyrics)



class LyricsModeFetcher(BaseLyricsFetcher):

    HOME = 'https://www.lyricsmode.com'
    url_pattern = 'https://www.lyricsmode.com/lyrics/{char}/{artist}/{title}.html'
    disallowed = re.compile(r'[^\w\d\s-]')
    strike = re.compile(r'[\s-]+')


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
        except HTTPError:
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
