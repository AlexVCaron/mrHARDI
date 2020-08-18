# Magic Monkey

Magic Monkey is a pipelining code base focused at processing and computing 
denoised images and metrics on MRI volumes of monkey, macaque and chimpanzee
brains. It takes as inputs diffusion weighted acquisitions, as well as 
anatomical images, masks, and others images when available.

As outputs, it offers, in addition to basic DTI, some more advanced 
reconstruction models like fiber Orientation Distribution Function and 
Multi-Tensor Distribution estimation (DIAMOND). The library also support 
Tensor-Valued encoding, and can output DIAMOND and ODF metrics using those.

## Installation

Magic Monkey uses a load of different dependencies to compute the different 
metrics and carry out some pre-processing computations. Those have all been 
wrapped inside a singularity, to ease out and shorten the installation process.

### Linux users

#### Requirements

- [Singularity 3](https://sylabs.io/guides/3.0/user-guide/installation.html)
- Python 3.7

#### Installation

The whole library can be installed by installing the requirements

> pip install -r requirements.txt

and then initiating the setup script using python 3.7

> python3 setup.py install

### Other platforms

Singularity however isn't available on Windows. We refer those users to the 
**Vagrant Installation** section of the readme for an alternative. For similar 
reasons, if there is any problems installing the library and running the tests 
on a Mac OSX operating system, the user should try using Vagrant.

## Vagrant Installation

#### Requirements

- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
- [Vagrant](https://www.vagrantup.com/downloads.html)
- [Vagrant manager](https://www.vagrantmanager.com/downloads/)

To automate the deployment of the library across different systems and on 
multiple instances, a Vagrant definition has been implemented. This also 
allows singularity to run on instead unsupported platforms like Windows.

#### Pre-installation

Some platforms can be picky on symbolic links (Windows is a good example). In 
order to allow ansible to provision the virtual machine correctly, run the 
installation commands in an elevated prompt or allow their creation to users.

#### Installation

To raise a new instance, simply call

> vagrant up

This will create a new virtual machine with the specifications defined in the 
Vagrantfile at the root of the library, provisioned with all Magic Monkey's 
dependencies and libraries.

### Running code

Once the virtual machine up and running, the pipelines can be run using ssh and 
the right python interpreter containing Magic Monkey.

It can be found in a folder located alongside this Readme, *vm/python*, related 
to the folder */shared_python* on the virtual machine itself.

In addition to this folder, the folder of the project is also made available on 
the virtual machine, at */home/vagrant/magic_monkey*.

A direct ssh connection can be made running the following command inside the 
project's directory

> vagrant ssh
