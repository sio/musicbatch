'''
Manage music metadata with HODS
'''
import os.path


VARIOUS_ARTISTS = 'Various Artists'

METADATA_DIRECTORY = '.meta'
METADATA_YAML = os.path.join(METADATA_DIRECTORY, 'info.yml')
METADATA_WHATCD = os.path.join(METADATA_DIRECTORY, 'whatcd.json')
METADATA_HTML = os.path.join(METADATA_DIRECTORY, 'info.html')
