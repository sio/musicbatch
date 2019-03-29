'''
Unit tests for lyrics fetchers
'''


from unittest import TestCase

from goodies.lyrics import BaseLyricsFetcher


class HelperFunctions(TestCase):
    def setUp(self):
        self.fetcher = BaseLyricsFetcher()


    def test_the(self):
        dataset = (
            # source, result, position
            ('Beatles, the', 'The Beatles', 'start'),
            ('Beatles,the', 'The Beatles', 'start'),
            ('Amaranthe', 'Amaranthe', 'start'),
            ('The Beatles', 'The Beatles', 'start'),
            ('The Beatles', 'Beatles, the', 'end'),
            ('Theater', 'Theater', 'end'),
            ('Beatles, the', 'Beatles, the', 'end'),
            ('Amaranthe', 'Amaranthe', 'end'),
            ('The Beatles', 'Beatles', None),
            ('Beatles, the', 'Beatles', None),
            ('Amaranthe', 'Amaranthe', None),
            ('Theater', 'Theater', None),
        )
        for source, result, position in dataset:
            with self.subTest(source=source, result=result, position=position):
                self.assertEqual(self.fetcher.fix_the(source, position), result)
