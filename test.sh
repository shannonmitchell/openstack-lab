#!/bin/bash

#virsh vol-create-as homepool classroom.example.com.img 80G --format qcow2
#virt-install --connect qemu:///system --name classroom.example.com --ram 2048 --disk vol=homepool/classroom.example.com.img --network network=default --network network=labnetwork --os-variant rhel7 --graphics vnc --virt-type kvm --cdrom /home/images/centos7.iso
#virt-install --connect qemu:///system --name classroom.example.com --ram 2048 --disk vol=homepool/classroom.example.com.img,format=qcow2 --network network=default --network network=labnetwork --os-variant rhel7 --graphics vnc --virt-type kvm --location=/home/images/centos7.iso --initrd-inject=/data/documents/certifications/classroom.example.com.ks --extra-args='ks=file:/classroom.example.com.ks'


virt-install \
--connect qemu:///system \
--name deploy \
--ram 512 \
--disk pool=storage,size=8,bus=virtio,sparse=false \
--network network=management,model=e1000 \
--network network=overlay,model=e1000 \
--network network=storage,model=e1000 \
--network network=management,model=e1000 \
--network network=overlay,model=e1000 \
--network network=storage,model=e1000 \
--location=http://us.archive.ubuntu.com/ubuntu/dists/xenial/main/installer-amd64/ \
--initrd-inject=./files/preseed.cfg \
--extra-args="console=tty0 console=ttyS0,115200n8 serial locale=en_GB.UTF-8 console-setup/ask_detect=false keyboard-configuration/layoutcode=hu file=file:/preseed.cfg quiet" \
--os-type=linux \
--os-variant=ubuntu16.04 \
--virt-type kvm \
--nographics

virt-install --connect qemu:///system --name deploy --ram 512 --disk pool=storage,size=8,bus=virtio,sparse=false --network network=management,model=e1000 --network network=overlay,model=e1000 --network network=storage,model=e1000 --network network=management,model=e1000 --network network=overlay,model=e1000 --network network=storage,model=e1000 --location=http://us.archive.ubuntu.com/ubuntu/dists/xenial/main/installer-amd64/ --initrd-inject=./files/preseed.cfg --extra-args="console=tty0 console=ttyS0,115200n8 serial locale=en_GB.UTF-8 console-setup/ask_detect=false keyboard-configuration/layoutcode=hu file=file:/preseed.cfg quiet" --os-type=linux --os-variant=ubuntu16.04 --virt-type kvm --nographics
