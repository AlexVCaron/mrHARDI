# -*- mode: ruby -*-
# vi: set ft=ruby :

# REMEMBER : Install vagrant plugin vagrant-disksize

# Place your configuration here, those values will be used in the script bellow
# Refer to the variable base_config for the acceptable configuration options
configuration = {}

# Don't touch this part of the script
base_config = {
  base_box: {name: "avcaron/mmy-base-box", ver: "0.3.0"},
  network: {private: {name: "private_network", ip: "192.168.77.101"}},
  vm: {name: "MAGIC-MONKEY_vbox", cpu: "3", ram: "10240", disk: "300GB"},
  build: {type: :develop, cpu: 3, verbose: "vvvv", hostname: "MMY-host"}
}
base_config.merge(configuration)

network = base_config[:network]
vm = base_config[:vm]
build = base_config[:build]

Vagrant.configure("2") do |config|
  # VM machine specific configuration
  config.disksize.size = vm[:disk]
  config.vm.provider "virtualbox" do |vb|
    vb.name = vm[:name]
    vb.linked_clone = true
    vb.memory = vm[:ram]
    vb.cpus = vm[:cpu]
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/shared_python", "1"]
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/vagrant", "1"]
  end

  # Get base vm config from vagrant
  config.vm.define build[:hostname] do |h|
    h.vm.box = base_config[:base_box][:name]
    h.vm.box_version = base_config[:base_box][:ver]
  end

  # Private IP address to access the VM
  config.vm.network network[:private][:name], ip: network[:private][:ip] if network.key?(:private)

  # Shared folders to manage shared python installation across the host and the remote
  config.vm.synced_folder "vm/python", "/shared_python", create: true, mount_options: ["dmode=775,fmode=777"]
  config.vm.synced_folder ".", "/home/vagrant/magic_monkey"
  config.vm.synced_folder ".", "/vagrant"

  # VM provisioning via ansible playbook
  config.vm.provision "ansible_local" do |ansible|
    ansible.playbook = "vm/ansible/setup.yml"
    ansible.become = true
    ansible.extra_vars = {
      n_procs: build[:cpu]
    }
    ansible.groups = {
      build[:type] => [build[:hostname]]
    }
    ansible.verbose = build[:verbose]
  end
end
