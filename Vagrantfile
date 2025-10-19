Vagrant.configure("2") do |config|
    config.vm.box = "generic/ubuntu2204"
    config.vm.network "private_network", ip: "192.168.56.10"
    # REMOVIDO: libvirt.memory = 4096 / libvirt.cpus = 2
    # O Vagrant irá usar o provedor padrão (VirtualBox no Windows)
    config.vm.provision "shell", path: "config.sh"
    config.vm.synced_folder "./web", "/home/vagrant/web",
        type: "virtualbox" # Mude o tipo de pasta sincronizada para VirtualBox
end