# Batch processing tools for music files

## Project status

In development, but already usable. Breaking changes are to be expected.



## Overview

This repo provides command line tools and Python interfaces for batch
processing large collections of music files:

- Transcoding the whole library (or parts of it) to another format, e.g. for
  exporting to a portable media player
- Fetching and displaying lyrics for music files
- Generating and managing album metadata with [HODS files](https://hods.ml/schemas/)


## Installation

1. Install Python package: `pip install
"https://github.com/sio/musicbatch/tarball/master"`

2. Install [FFmpeg](http://ffmpeg.org) - it's used as audio encoding backend.



## Usage

This package provides command line interface and Python modules for
incorporating into your scripts.

Command line interface may be accessed via `music` command or by executing the
top-level module directly: `python -m musicbatch`. Main CLI entry point
resembles git behavior - it relays all work to one of subcommands:

- lyrics
- metadata
- transcoder

### lyrics

```
usage: music lyrics [-h] [--database FILE] [--scan-library DIR]
                    [--retry-scheduled]
                    [ARTIST] [TITLE]

Interact with local lyrics database. Populate the database with lyrics from
web sources for all songs in a given directory or return the text of a single
song if ARTIST and TITLE are specified.

positional arguments:
  ARTIST              Song artist
  TITLE               Song title

optional arguments:
  -h, --help          show this help message and exit
  --database FILE     Path to local lyrics database (default: ~/.lyrics.db)
  --scan-library DIR  Populate local lyrics database with texts for all songs
                      in this directory (recursive)
  --retry-scheduled   Retry fetching lyrics that were unavailable in previous
                      runs
```

### metadata

```
usage: music metadata [-h] [--recursive] [--location LOCATION]
                      (--generate | --add-categories CATEGORIES
                      | --set-categories CATEGORIES | --del-categories CATEGORIES
                      | --clear-categories) DIR

Manage music metadata with YAML files

positional arguments:
  DIR                   Directory with music files

optional arguments:
  -h, --help            show this help message and exit
  --recursive           Process all nested directories within DIR
  --location LOCATION   Relative path to metadata file
                        (default=.meta\info.yml)
  --generate            Create metadata file(s) for specified directory
  --add-categories CATEGORIES
                        Add specified category or categories (comma-separated
                        list) to metadata file
  --set-categories CATEGORIES
                        Replace categories in metadata file with specified
                        values
  --del-categories CATEGORIES
                        Remove specified categories from metadata file(s)
  --clear-categories    Remove all categories from metadata file(s)
```


### transcoder

```
usage: music transcoder [-h] [--newconfig] CONFIG

Batch transcode music files according to the provided configuration file

positional arguments:
  CONFIG       Path to YAML description of the transcoding job

optional arguments:
  -h, --help   show this help message and exit
  --newconfig  Create new configuration file from template and open it for
               editing

This program relies on FFmpeg <http://ffmpeg.org> for audio encoding.
Please make sure it's installed
```

Transcoding job is described with a YAML file. See sample below and refer to
[JSON schema](musicbatch/transcoder/schema.json) for more information.

```yaml
name: Sansa Clip Zip  # required: transcoding job identifier

input:  # required: at least one directory path
  - /home/user/music
  - /media/torrents/music

output:
  directory: /media/user/SANSA_SD  # required: path to destination directory
  pattern: '{artist}/{year} - {album}/{number} - {title}'  # optional: file hierarchy in destination directory
  format: vorbis  # optional: vorbis(default)/opus/lame/aac/copy/symlink
  quality: q5  # optional: default value depends on selected output format
  lossy_source: copy  # optional: copy (default) / allow_bad_transcodes / skip
  category_blacklist:  # optional: select which albums to transcode based on HODS metadata files
  # also: category_whitelist
    - foo
    - bar

extras:
  lyrics: /path/to/lyrics/database-or-directory  # optional: path to lyrics database / lyrics directory / null or false to skip copying lyrics
  cover: 96  # optional: max size of cover art in pixels / null, false to disable copying covers
```



## Support and contributing

If you need help using these tools from command line or including them into
your Python project, please create
**[an issue](https://github.com/sio/musicbatch/issues)**. Issues are also the
primary venue for reporting bugs and posting feature requests. General
discussion related to this project is also acceptable and very welcome!

In case you wish to contribute code or documentation, feel free to open **[a
pull request](https://github.com/sio/musicbatch/pulls)**. That would certainly
make my day!

I'm open to dialog and I promise to behave responsibly and treat all
contributors with respect. Please try to do the same, and treat others the way
you want to be treated.

If for some reason you'd rather not use the issue tracker, contacting me via
email is OK too. Please use a descriptive subject line to enhance visibility
of your message. Also please keep in mind that public discussion channels are
preferable because that way many other people may benefit from reading past
conversations. My email is visible under the GitHub profile and in the commit
log.



## License and copyright

Copyright 2019 Vitaly Potyarkin

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.



## Development roadmap

- Manage album metadata
    - Generate info page
- Extras
    - Add support for aoTuV path
- JSON Schema
    - Add default values to json schema
    - Generate documentation from json schema
- `git grep TОDО`
