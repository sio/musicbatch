'''
Some test cases for lyrics fetchers that can only be run interactively
'''

import sys
from traceback import format_exc


TEST_SONGS = (
    # artist, title, explanation
    ('Animaniacs', 'Yakko\'s World', 'rich formatting'),
    ('Apocalyptica', 'No education', 'instrumental'),
    ('Beatles, the', 'Yellow Submarine', 'artist with "the" in the name'),
    ('Lauren Daigle', 'You Say', 'normal song'),
    ('ARRRRRRTIST', 'TITTLE', 'not found'),
    ('Kiroro', 'Mirae', 'japanese lyrics, romanized'),
    ('Kiroro', '帰る場所', 'japanese lyrics, unmodified'),
    ('Hemanta Mukherjee', 'Tumi Robe Nirobe', 'bengali lyrics, unmodified'),
    ('Hemanta Mukherjee & Lata Mangeskar', 'Tumi Robe Nirobe', 'bengali lyrics, unmodified'),
    ('Пилот', 'Шнурок', 'cyrillic lyrics'),
    ('Flёur', 'Всё вышло из-под контроля', 'cyrillic lyrics'),
)


def run_tests(fetcher_class, filename=None):
    fetcher = fetcher_class()

    if filename:
        output = open(filename, 'w', encoding='utf-8')
        show = lambda x: output.write(x)
    else:
        show = lambda x: print(x, end='')

    for artist, title, explanation in TEST_SONGS:
        try:
            lyrics = fetcher(artist, title)
        except Exception:
            lyrics = format_exc()
        show(
            '---\nTesting the song:   {artist} - {title}\n'
            'Reason for testing: {explanation}\n\n{lyrics}\n\n'
            .format(**locals())
        )

    if filename:
        output.close()
