'''
Helper tools for cyrillic captions
'''

def transliterate(text, placeholder='_', override=None):
    '''Simple transliteration'''

    ru = {  'а': 'a',
            'б': 'b',
            'в': 'v',
            'г': 'g',
            'д': 'd',
            'е': 'e',
            'ё': 'e',
            'ж': 'zh',
            'з': 'z',
            'и': 'i',
            'й': 'y',
            'к': 'k',
            'л': 'l',
            'м': 'm',
            'н': 'n',
            'о': 'o',
            'п': 'p',
            'р': 'r',
            'с': 's',
            'т': 't',
            'у': 'u',
            'ф': 'f',
            'х': 'h',
            'ц': 'c',
            'ч': 'ch',
            'ш': 'sh',
            'щ': 'sch',
            'ъ': '',
            'ы': 'yi',
            'ь': '',
            'э': 'e',
            'ю': 'yu',
            'я': 'ya'}

    if override:
        ru.update(override)

    latin = dict()
    for i in range(256):
        char = chr(i)
        latin[char] = char

    letters = dict()
    for i in (ru, latin):
        letters.update(i)

    new_text = str()
    for c in text:
        if c.isupper():
            new_text += letters.get(c.lower(), placeholder).upper()
        else:
            new_text += letters.get(c, placeholder)

    return new_text
