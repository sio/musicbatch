'''
Manage music metadata with HODS
'''
import os.path


VARIOUS_ARTISTS = 'Various Artists'

METADATA_DIRECTORY = '.meta'
METADATA_YAML = os.path.join(METADATA_DIRECTORY, 'info.yml')
METADATA_WHATCD = os.path.join(METADATA_DIRECTORY, 'whatcd.json')
METADATA_HTML = os.path.join(METADATA_DIRECTORY, 'info.html')

# TODO: iniitial building of metadata
#   1. Build database of archived API responses from What.CD
#   2. Distribute those responses in the torrents directory
#   3. Generate metadata for each file in torrents directory
