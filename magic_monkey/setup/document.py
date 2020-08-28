from distutils.log import INFO
from os import chdir, getcwd
from os.path import exists, isdir

from setuptools import Command


class Document(Command):
    description = 'Create documentation for library and apps'
    user_options = [
        ('chdir=', None, 'path where to generate the doc (will overwrite)')
    ]

    def run(self):
        cwd = getcwd()
        self.announce('Generating documentation', level=INFO)
        self.spawn([
            'pip3', 'install', '-U', '-r',
            'documentation/_cache/requirements.txt'
        ])

        chdir('documentation/_cache')

        self.spawn(['make', 'clean'])

        command = ['make', 'html']
        if self.chdir:
            command.append('BUILDDIR="{}"'.format(self.chdir))

        self.spawn(command)
        chdir(cwd)

    def initialize_options(self):
        self.chdir = None

    def finalize_options(self):
        if self.chdir:
            if not exists(self.chdir):
                self.announce(
                    'Creating documentation path : {}'.format(self.chdir),
                    level=INFO
                )
                self.mkpath(self.chdir)
            elif not isdir(self.chdir):
                raise AttributeError(
                    "The path passed is an existing file : {}".format(
                        self.chdir
                    )
                )
