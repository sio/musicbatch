from setuptools import setup, find_packages


setup(
    name='musicbatch',
    version='0.0.1-git',
    description='Batch processing tools for music files',
    url='https://github.com/sio/musicbatch',
    author='Vitaly Potyarkin',
    author_email='sio.wtf@gmail.com',
    license='Apache',
    platforms='any',
    entry_points={
        'console_scripts': [
            'transcoder=musicbatch.transcoder.app:run',
            'lyrics=musicbatch.lyrics.app:run',
        ],
    },
    packages=find_packages(exclude=('tests',)),
    include_package_data=True,
    install_requires=[
        # Transcoder
        'mutagen',
        'pillow',
        'pydub',
        'ruamel.yaml',
        'jsonschema',
        'hods @ https://github.com/sio/hods/archive/master.zip',
        # Lyrics + Scrapehelper
        'requests',
        'lxml',
        'sqlalchemy',
    ],
    python_requires='>=3.3',
    zip_safe=True,
)
