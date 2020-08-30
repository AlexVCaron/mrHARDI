import os
import platform
from distutils.log import INFO
from os import chdir, getcwd
from os.path import exists, isdir

from setuptools import Command


class Document(Command):
    description = 'Create documentation for library and apps'
    user_options = []
    # user_options = [
    #     ('chdir=', None, 'path where to generate the doc (will overwrite)')
    # ]

    def run(self):
        cwd = getcwd()
        self.announce('Generating documentation', level=INFO)
        self.spawn([
            'pip3', 'install', '-U', '-r',
            'documentation/_cache/requirements.txt'
        ])

        chdir('documentation/_cache')

        command = [self._make(), 'clean']

        self.spawn(command)

        command = [self._make(), 'html']

        self.spawn(command)

        chdir(cwd)

    def initialize_options(self):
        pass
        # self.chdir = None

    def finalize_options(self):
        pass
        # if self.chdir:
        #     if not exists(self.chdir):
        #         self.announce(
        #             'Creating documentation path : {}'.format(self.chdir),
        #             level=INFO
        #         )
        #         self.mkpath(self.chdir)
        #     elif not isdir(self.chdir):
        #         raise AttributeError(
        #             "The path passed is an existing file : {}".format(
        #                 self.chdir
        #             )
        #         )

    def _make(self):
        sys = platform.system()
        return "make.cmd" if sys == "Windows" else "make"
