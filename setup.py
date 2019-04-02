from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess
import sys


class InstallDependenciesByDirectLink(install):
    direct_links = [
        'https://github.com/sio/hods/archive/master.zip#egg=hods',
    ]
    def run(self):
        if self.direct_links:
            subprocess.call(
                [sys.executable, '-m', 'pip', 'install'] + self.direct_links
            )
        super().run()


setup(
    name='musicbatch',
    version='0.0.1',
    description='Batch processing of music files',
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
    cmdclass={'install': InstallDependenciesByDirectLink},
    install_requires=[
        # Transcoder
        'mutagen',
        'pillow',
        'pydub',
        'ruamel.yaml',
        # Lyrics + Scrapehelper
        'requests',
        'lxml',
        'sqlalchemy',
        # 'hods' package will be installed via direct link since it's not published on PyPA
    ],
    python_requires='>=3.3',
    zip_safe=True,
)
