# ansible-packer-vagrant-openstack

Ansible scripts to build operating system images using Packer and Vagrant, 
exporting to an Openstack image.

## Required software:

- Ansible (http://www.ansible.com/home)
- Packer (https://www.packer.io/)
- Vagrant (https://www.vagrantup.com/)
- qemu-img (available for OS X in Brew's qemu package)

These scripts assume that you are using Virtualbox to back Vagrant boxes.

## You'll also need:

- An ISO image you would like to install (this example uses CentOS 7), place 
  it in packer/ directory (remember to update template.json checksums).

Tested on OS X 10.10.

## Running the play

Simply run:
```
ansible-playbook -i hosts build-image.yml
```

Pro-tip: No Packer build (when you want to debug your scripts more quickly and you
already have a base Packer build):
```
ansible-playbook -i hosts build-image.yml -e 'no_packer_build=yes'
```

If everything was successful, you'll find the QCOW2 image in your Ansible directory.

