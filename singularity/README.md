# Magic-monkey Singularity image

This directory contains the required files to build the singularity image 
containing the whole collection of applications and configurations of the 
project. It is a plus when using the nextflow library to have this image 
ready and available, since no setup is needed for the user.

## Requirements

- [Singularity 3](https://sylabs.io/guides/3.0/user-guide/installation.html)
- Python 3 for initial preparation of the project's wheel

## Content of the image

- Mrtrix 3
- ANTs Registration
- FSL
- Diamond
- Python 3 with libraries
    - Scilpy
    - Magic-monkey
    - Dipy
    - Numpy / Scipy
    - Nibabel / Pynrrd
- Cuda 9.1

## Building the image

Singularity makes it easy to build the image in one line of code. Before 
calling the build sequence, ensure that your shell's current directory is 
the one containing this Readme. Then, call

> sudo singularity build <image_name>.<sif/simg> magic_monkey_singularity.def

The build process takes about half an hour on a conventional 3 cores processor.

## Using the packaged applications

All the applications listed above can be called directly on the singularity 
using

> singularity exec \<image> \<application>

For example to call the *dwidenoise* algorithm from Mrtrix, use

> singularity exec \<image> dwidenoise \<args>

To make your data available to the singularity, add the option *-B* before
**exec**, with a comma separated list of the paths to bind.

> singularity -B \<path 1>,\<path 2> exec ...
