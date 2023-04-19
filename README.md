[![Actions Status](https://github.com/AlexVCaron/mrHARDI/workflows/Release%20build/badge.svg)](https://github.com/AlexVCaron/mrHARDI/actions/workflows/build-release.yml)
[![Actions Status](https://github.com/AlexVCaron/mrHARDI/workflows/Development%20PR%20builds/badge.svg)](https://github.com/AlexVCaron/mrHARDI/actions/workflows/build-develop.yml)
[![Latest Stable Version](https://img.shields.io/github/v/release/AlexVCaron/mrHARDI)](https://github.com/AlexVCaron/mrHARDI/releases)

# mrHARDI

mrHARDI is a pipelining code base focused at processing and computing 
denoised images and metrics on MRI volumes of monkey, macaque and chimpanzee
brains. It takes as inputs diffusion weighted acquisitions, as well as 
anatomical images, masks, and others images when available.

As outputs, it offers, in addition to basic DTI, some more advanced 
reconstruction models like fiber Orientation Distribution Function and 
Multi-Tensor Distribution estimation (DIAMOND). The library also support 
Tensor-Valued encoding, and can output DIAMOND and ODF metrics using those.

## Installation

mrHARDI uses a load of different dependencies to compute the different 
metrics and carry out some pre-processing computations. Those have all been 
wrapped inside a singularity, to ease out and shorten the installation process.

### Linux users

#### Requirements

- [Singularity](https://docs.sylabs.io/guides/3.0/user-guide/installation.html) 3.7.1 or higher, or [Docker](https://docs.docker.com/engine/install/)
- Python 3.7

#### Installation

The whole library can be installed by installing the requirements

> pip install -r requirements.txt

and then initiating the setup script using python 3.7

> python3 setup.py install

### Other platforms

Singularity and Nextflow aren't available on Windows. We refer those users to 
the **Vagrant Installation** section of the readme for an alternative. For 
similar reasons, if there is any problems installing the library and running 
the tests on a Mac OSX operating system, the user should try using Vagrant.

## Usage

The code base is accessible via numerous points. The whole python library can 
be imported using the package **mrHARDI**. Most of the logic of the code 
base can be found under **mrHARDI.compute** and **mrHARDI.traits**.

Also, the various applications and configuration options are accessible by 
command-line. Once the project is setup, built and installed, they can be 
called using the alias **mrhardi**, followed by the name of the 
application to open. For more information, call *mrhardi --help*.

Finally, a collection of *Nextflow* modules and workflows have been developed 
for usage with mrHARDI. They automate the processing of large volumes of images 
and handle the spreading of computing tasks on multiple scales of processing 
hardware. This library can be found in the 
[mrHARDIflow](https://github.com/AlexVCaron/mrHARDIflow) repository.

This duality of entry points allows for a better and faster prototyping from 
the developer, since all configuration of the applications is done via python 
and can be completed by only calling the command-line apps. This makes it 
easier to debug and optimize each sub-assembly, with no overhead from Nextflow 
when it isn't required to test the actual pipeline structure.

## Vagrant Installation

The Vagrant VM allows for an easy installation of the whole stack of the 
project. It includes *singularity*, *nextflow* and a standalone version of 
*python 3* preloaded with the *mrHARDI* project.

#### Requirements

- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
- [Vagrant](https://www.vagrantup.com/downloads.html)
- [Vagrant manager](https://www.vagrantmanager.com/downloads/)

To automate the deployment of the library across different systems and on 
multiple instances, a Vagrant definition has been implemented. This also 
allows singularity to run on instead unsupported platforms like Windows.

#### Vagrant configuration

Some plugins are required by vagrant for it to setup and provision the vm 
correctly. To install them, enter the following commands in a terminal : 

> vagrant plugin install vagrant-vbguest

> vagrant plugin install vagrant-disksize

> vagrant plugin install vagrant-winnfsd

#### Pre-installation

Some platforms can be picky on symbolic links (Windows is a good example). In 
order to allow ansible to provision the virtual machine correctly, run the 
installation commands in an elevated prompt or allow their creation to users.

#### Installation

To raise a new instance, simply call

> vagrant up

This will create a new virtual machine with the specifications defined in the 
Vagrantfile at the root of the library, provisioned with all mrHARDI's 
dependencies and libraries.

### Running code

Once the virtual machine up and running, the pipelines can be run using ssh and 
the right python interpreter containing mrHARDI.

It can be found in a folder located alongside this Readme, *vm/python*, related 
to the folder */shared_python* on the virtual machine itself.

In addition to this folder, the folder of the project is also made available on 
the virtual machine, at */home/vagrant/mrHARDI*.

A direct ssh connection can be made running the following command inside the 
project's directory

> vagrant ssh

### FAQ

- On windows 10, if the network interface fails to reconnect and prevents 
  Vagrant to boot the vm, then :
  - In *VirtualBox Manager*, delete the mentioned interface from the list
  - On Widows, in **Device Manager > Network adapters**, restart the interface 
    named *VirtualBox Host-Only Ethernet Adapter*
