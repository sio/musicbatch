'''
Batch transcode music files according to the provided config
'''


from transcoder.logging import log  # Initialize logger


LOSSY_EXTENSIONS = {'ogg', 'mp3', 'aac'}
LOSSLESS_EXTENSIONS = {'flac', 'ape', 'wav', 'pcm', 'raw'}
KNOWN_EXTENSIONS = LOSSY_EXTENSIONS | LOSSLESS_EXTENSIONS


DEFAULT_CONFIG = {
    'name': 'Transcoding Job',
    'pattern': '{artist} - {year} - {album}/{number} {title}',
    'format': 'vorbis',
    'quality': 'q5',
    'lossy_source': 'copy',
    'cover': 250,
}
