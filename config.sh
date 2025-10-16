#! /bin/bash
set -e

sudo apt update && sudo apt upgrade -y

sudo apt install -y python3 python3-pip mysql-server cgroup-tools
# sudo pip3 install flask mysql-connector-python

mkdir -p /home/vagrant/web

# sudo chown -R vagrant:vagrant /home/vagrant/web
