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

## Usage

The code base is accessible via numerous points. The whole python library can 
be imported using the package **magic_monkey**. Most of the logic of the code 
base can be found under **magic_monkey.compute** and **magic_monkey.traits**.

Also, the various applications and configuration options are accessible by 
command-line. Once the project is setup, built and installed, they can be 
called using the alias **magic-monkey**, followed by the name of the 
application to open. For more information, call *magic-monkey --help*.

Finally, a collection of *Nextflow* modules and workflows can be found under 
the nextflow directory. In addition of the fully implemented pipelines and 
workflows of *Magic Monkey*, can be found modules and workflows that 
inferfaces fluently with Mri processing libraries as well as with this code 
base.

This duality of entry points allows for a better and faster prototyping from 
the developer, since all configuration of the applications is done via python 
and can be completed by only calling the command-line apps. This makes it 
easier to debug and optimize each sub-assembly, with no overhead from Nextflow 
when it isn't required to test the actual pipeline structure.

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

### FAQ

- On windows 10, if the network interface fails to reconnect and prevents 
  Vagrant to boot the vm, then :
  - In *VirtualBox Manager*, delete the mentioned interface from the list
  - On Widows, in **Device Manager > Network adapters**, restart the interface 
    named *VirtualBox Host-Only Ethernet Adapter*

### FAQ

- On windows 10, if the network interface fails to reconnect and prevents 
  Vagrant to boot the vm, then :
  - In *VirtualBox Manager*, delete the mentioned interface from the list
  - On Widows, in **Device Manager > Network adapters**, restart the interface 
    named *VirtualBox Host-Only Ethernet Adapter*