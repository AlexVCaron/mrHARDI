# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Get base vm config from vagrant
  config.vm.box = "avcaron/mmy-base-box"
  config.vm.box_version = "0.2.0"

  # Private IP address to access the VM
  config.vm.network "private_network", ip: "192.168.77.101"

  # Shared folders to manage shared python installation across the host and the remote
  config.vm.synced_folder "vm/python", "/shared_python", create: true, mount_options: ["dmode=775,fmode=777"]
  config.vm.synced_folder ".", "/home/vagrant/magic_monkey"
  config.vm.synced_folder ".", "/vagrant"

  # VM machine specific configuration
  config.vm.provider "virtualbox" do |vb|
    vb.name = "MAGIC-MONKEY_vbox"
    vb.linked_clone = true
    vb.memory = "1024"
    vb.cpus = "2"
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/shared_python", "1"]
  end

  # VM provisioning via ansible playbook
  config.vm.define "MMY-host"

  config.vm.provision "ansible_local" do |ansible|
    ansible.playbook = "vm/ansible/setup.yml"
    ansible.become = true
    ansible.extra_vars = {
      n_procs: 3
    }
    ansible.groups = {
      "develop" => ["MMY-host"]
    }
    ansible.verbose = "vvvv"
  end
end
