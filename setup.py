from setuptools import setup, find_packages

setup(
    name='magic-monkey',
    version='0.1.0',
    packages=find_packages(exclude=["vm/", "test", "test/", "test.*", ".*/"]),
    url='',
    license='',
    author='Alex Valcourt Caron',
    author_email='alex.valcourt.caron@usherbrooke.ca',
    description='',
    python_requires='>=3.7'
)
