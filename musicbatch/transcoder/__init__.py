'''
Batch transcode music files according to the provided config
'''


LOSSY_EXTENSIONS = {'ogg', 'mp3', 'aac', 'm4a', 'opus'}
LOSSLESS_EXTENSIONS = {'flac', 'ape', 'wav', 'pcm', 'raw'}
KNOWN_EXTENSIONS = LOSSY_EXTENSIONS | LOSSLESS_EXTENSIONS


DEFAULT_CONFIG = {
    'name': 'Transcoding Job',
    'pattern': '{artist} - {year} - {album}/{number} {title}',
    'format': 'vorbis',
    'quality': None,
    'lossy_source': 'copy',
    'cover': 250,
    'lyrics': None,
}
CONFIG_ENCODING = 'utf-8'
