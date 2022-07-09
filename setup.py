from setuptools import setup, find_packages

setup(
    name='mrHARDI',
    version='0.1.0',
    packages=find_packages(exclude=[
        "vm/", "test", "test/", "test.*",
        ".nextflow/", ".vagrant/", "nextflow/"
    ]),
    url='',
    license='MIT',
    author='Alex Valcourt Caron',
    author_email='alex.valcourt.caron@usherbrooke.ca',
    description='',
    entry_points={
        'console_scripts': [
            'mrhardi=mrHARDI.main_app:launch_new_instance'
        ],
        'distutils.commands': ['document=mrHARDI.setup:Document']
    },
    python_requires='>=3.7,<3.10',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Operating System :: POSIX :: Linux"
    ]
)
