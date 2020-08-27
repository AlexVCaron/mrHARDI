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
        command = ['magic-monkey', '--document']
        self.announce(
            'Generating documentation : {}'.format(command), level=INFO
        )
        self.spawn(command)
        chdir(self.chdir)

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

            cwd = getcwd()
            chdir(self.chdir)
            self.chdir = cwd
