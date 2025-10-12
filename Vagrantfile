Vagrant.configure("2") do |config|
    config.vm.box = "generic/ubuntu2204"
    config.vm.provider :libvirt do |libvirt|
        libvirt.memory = 4096
        libvirt.cpus = 2
    end
    config.vm.provision "shell", path: "config.sh"
    config.vm.synced_folder ".", "/home/vagrant"
end