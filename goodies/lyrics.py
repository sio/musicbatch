'''
Fetch lyrics from public collections
'''

import re
from urllib.parse import quote

from lxml import etree

from goodies.fetch import BaseDataFetcher



class BaseLyricsFetcher(BaseDataFetcher):
    '''Base class for all lyrics fetchers'''

    url_pattern = NotImplemented
    _regex = {
        'the_start': re.compile(r'^\s*the\s+(.*)', re.IGNORECASE),
        'the_end': re.compile(r'(.*)(?:,\s*|[^,]\s+)the\s*$', re.IGNORECASE),
    }


    @classmethod
    def fix_the(cls, caption, position='start'):
        '''
        Fix location of the "The" in a given caption

        If "the" is present, it will be moved either to the start or to the end
        of line according to the value of `position`
        '''
        regex = cls._regex
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

    api = 'http://lyrics.wikia.com/api.php'
    marker = re.compile(r'^.*<lyrics>(.*)</lyrics>.*$', re.DOTALL|re.IGNORECASE)
    noise = re.compile(r"''+", re.DOTALL)

    def fetch(self, artist, title):
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
            return None  # lyrics not found

        full_page_url = overview.xpath('url//text()')[0]
        html = self.parse_html(full_page_url, params=dict(action='edit'))
        wiki_text = html.xpath('//*[@id="wpTextbox1"]//text()')[0]
        lyrics = self.marker.sub(r'\1', wiki_text)
        return self.noise.sub('', lyrics).strip()
