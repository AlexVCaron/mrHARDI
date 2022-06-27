from setuptools import setup, find_packages

setup(
    name='magic-monkey',
    version='0.1.0',
    packages=find_packages(exclude=[
        "vm/", "test", "test/", "test.*",
        ".nextflow/", ".vagrant/", "nextflow/"
    ]),
    url='',
    license='',
    author='Alex Valcourt Caron',
    author_email='alex.valcourt.caron@usherbrooke.ca',
    description='',
    entry_points={
        'console_scripts': [
            'magic-monkey=magic_monkey.main_app:launch_new_instance'
        ],
        'distutils.commands': ['document=magic_monkey.setup:Document']
    },
    python_requires='>=3.7'
)
