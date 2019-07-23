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
            'music=musicbatch.app:run',
            'music-transcoder=musicbatch.transcoder.app:run',
            'music-lyrics=musicbatch.lyrics.app:run',
            'music-metadata=musicbatch.metadata.app:run',
        ],
    },
    packages=find_packages(exclude=('tests',)),
    include_package_data=True,
    install_requires=[
        'mutagen',
        'pillow',
        'pydub',
        'ruamel.yaml',
        'jsonschema',
        'hods @ https://github.com/sio/hods/tarball/master',
        'scrapehelper @ https://github.com/sio/scrapehelper/tarball/master',
        'lxml',
        'sqlalchemy',
    ],
    python_requires='>=3.3',
    zip_safe=True,
)
