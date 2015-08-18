# ansible-packer-vagrant-openstack

Ansible scripts to build operating system images using Packer and Vagrant, 
exporting to an Openstack image.

*Now this playbook also generates AMI and OVF images.*

## Required software:

- Ansible (http://www.ansible.com/home)
- Packer (https://www.packer.io/)
- Vagrant (https://www.vagrantup.com/)
- qemu-img (available for OS X in Brew's qemu package)

These scripts assume that you are using Virtualbox to back Vagrant boxes.

## Required setup for OVF images

Change "build_ovf_image" to true (from command line or playbook vars).

The import has only been tested on Virtualbox.

## Required setup for AMI images

Change "build_ami_image" to true (from command line or playbook vars).

Amazon EC2 command line tools installed: http://docs.aws.amazon.com/AWSEC2/latest/CommandLineReference/set-up-ec2-cli-linux.html
Amazon EC2 AMI tools installed: https://aws.amazon.com/developertools/368

Environment variables JAVA_HOME, EC2_HOME, EC2_AMITOOL_HOME and PATH properly set, 
example:

```
export EC2_HOME=/opt/local/ec2/ec2-api-tools-1.7.5.0/
export EC2_AMITOOL_HOME=/opt/local/ec2/ec2-ami-tools-1.5.7/
export PATH=$PATH:$EC2_HOME/bin:$EC2_AMITOOL_HOME/bin
export JAVA_HOME=$(/usr/libexec/java_home)
```

Please note that the EC2 AMI tools appear not to support MacOS X, but that can be
adequately (eg. ec2-bundle-vol won't work) fixed with these two commands.

```
cd $EC2_AMITOOL_HOME/lib/ec2/platform
sudo cp -a linux macosx
sudo cp -a linux.rb macosx.rb
```

Also you'll need to set your AWS_ACCESS_KEY and AWS_SECRET_KEY:

```
export AWS_ACCESS_KEY=XXXXXXXXXXXXXXXXXX
export AWS_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Then finally you'll need your client number (twelve digits from Amazon) and a X.509 
certificate from the IAM console (configure in the playbook build-image.yml vars 
section, amazon_private_key and amazon_certificate).

~~Finding a proper Amazon Kernel Image (PV-GRUB, hd00) for your region (place in amazon_region 
and amazon_kernel_image):~~
```
ec2-describe-images --region eu-central-1 -a -F image-type=kernel -F manifest-location=*pv-grub* | grep 'pv-grub.*hd00.*x86_64'
```
(This image uses HVM virtualization, but paravirtualization might work, just add kernel flavor
to manifest template)

## You'll also need:

- An ISO image you would like to install (this example uses CentOS 7), place 
  it in packer/ directory (place the iso image filename in build-image.yml variables).
  Example: 
  wget -Opacker/CentOS-7-x86_64-Minimal-1507-01.iso http://buildlogs.centos.org/rolling/7/isos/x86_64/CentOS-7-x86_64-Minimal-1507-01.iso
- Miscellaneous utilities (should come bundled with OS X): xmllint, tidy,
  openssl, perl, split, uuidgen

Tested on OS X 10.10, but should be easily adapted to Linux.

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
If you built an AMI image, it should be available under your AMI images.

