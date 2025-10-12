Vagrant.configure("2") do |config|
    config.vm.box = "generic/ubuntu2204"
    config.vm.network "private_network", ip: "192.168.56.10"
    config.vm.provider :libvirt do |libvirt|
        libvirt.memory = 4096
        libvirt.cpus = 2
    end
    config.vm.provision "shell", path: "config.sh"
    config.vm.synced_folder "./web", "/home/vagrant/web",
        type: "9p",
        mount_options: ['trans=virtio', 'version=9p2000.L']

end