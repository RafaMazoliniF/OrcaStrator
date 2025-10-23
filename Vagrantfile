Vagrant.configure("2") do |config|
    config.vm.box = "generic/ubuntu2204"
    config.vm.network "private_network", ip: "192.168.56.10"
    
    config.vm.provider :libvirt do |libvirt|
        libvirt.memory = 4096
        libvirt.cpus = 2
    end
    
    config.vm.provision "shell", path: "config.sh"
    
    # Use rsync instead of NFS
    config.vm.synced_folder "./web", "/home/vagrant/web",
        type: "rsync",
        rsync__exclude: ".git/"
end