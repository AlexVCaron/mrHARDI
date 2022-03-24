# Magic-monkey Singularity image

This directory contains the required files to build the singularity image 
containing the whole collection of applications and configurations of the 
project. It is a plus when using the nextflow library to have this image 
ready and available, since no setup is needed for the user.

## Requirements

- [Singularity 3](https://sylabs.io/guides/3.0/user-guide/installation.html)
- Python 3 for initial preparation of the project's wheel
- Diamond repository copied to an archive named **diamond_package.tar.gz** 
  (either contact *Benoît Scherrer* to request access to the official 
  repository or contact the administrator of this code base for a copy of the 
  singularity)

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
- Python 2.7 (comes vanilla, unloaded, we don't know what's inside. Use at your own risk, or please don't ...)

## Building the image

The building of the singularity for this project takes two steps.

### Building the heavy base singularity

The base image must first be built if none is available or if some changes 
need to be done to the base packages, that is :

- Mrtrix 3
- ANTs Registration
- FSL
- Diamond
- Cuda 9.1

Once in the directory **singularity/heavy**, call

> singularity build ../magic_monkey_heavy.sif magic_monkey_heavy.def

This will locally build a copy of the image, which will have to be 
uploaded to the *Singularity Library* in order for it to be take into 
account directly by the other definition file, or used locally using the 
local version of the final build file.

### Building the final image

Once a base image is secured, the final image can be built, in the 
directory **singularity/**, using :

> singularity build magic_monkey_singularity.sif magic_monkey.def

Alternatively, a local image can be provided as base for the final image 
build. To do so, use *magic_monkey_local.def* instead. Be sure the base 
singularity can be found in the **singularity** directory and that it is 
named **magic_monkey_heavy.sif**

To ensure the magic-monkey library installed inside the singularity is 
up-to-date and aligns with the requirements of the Nextflow library, be 
sure to position your local repository on the branch *feat/singularity_mmy* 
and that your local branch is up-to-date with the repository.

### Sanity check on built images

As of now, building the singularity will never lead to error, meaning you'll 
always end up with an image at the end, just maybe not filled with all the 
content that should be on it. This means that you should always check the 
build outputs and the executables on the final image.

A good indicator is the standard output of the build process. If anything 
happened, it will have at the end of it an error message that is quite hard 
to miss, with the error of the last program build cycle.

## Using the packaged applications

All the applications listed above can be called directly on the singularity 
using

> singularity exec \<image> \<application>

For example to call the *dwidenoise* algorithm from Mrtrix, use

> singularity exec \<image> dwidenoise \<args>

To make your data available to the singularity, add the option *-B* before
**exec**, with a comma separated list of the paths to bind.

> singularity -B \<path 1>,\<path 2> exec ...

## Developers

Building and rebuilding a Singularity can be time consuming. For this purpose, 
the definition file has been crafted to allow for installation checkpoints.

This means that updating a *sandbox* image is possible. After creating a first 
version of the image using

> sudo singularity build --sandbox \<image> magic_monkey.def

subsequent versions of it can be updated with

> sudo singularity build --update \<image> magic_monkey.def

It is unadvised to build the base heavy image under this mode, since it contains 
programs whose sources are too heavy for the update cycle of singularity. Only 
use this mode when developing directly on **magic-monkey** code or other 
lightweight python libraries.
