#!/usr/bin/python

import os
import sys
import uuid
import json
import jinja2
import libvirt
import argparse
import paramiko
import ipaddress
import subprocess
import configparser

# apt-get install python-configparsesr python-lvm2 python-libvirt

def deployRootKey(curhost, curuser, curpass):

    # Get the public root key
    pubkey = open('/root/.ssh/id_rsa.pub', 'r')
    pubkeytext = pubkey.read()
    pubkey.close() 
    
    # Copy it over
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(curhost, username=curuser, password=curpass)
    client.exec_command('mkdir -p ~/.ssh/')
    client.exec_command('echo "%s" > ~/.ssh/authorized_keys' % pubkeytext)
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')

def logit(log, logtype="INFO"):
    print "[%s]: %s" % (logtype, log)

def getConfigItem(config, section, item):

    try:
        curitem = config.get(section, item)
    except configparser.NoSectionError, e:
        logit(e, logtype="ERROR")
        sys.exit(1)
    except configparser.NoOptionError, e:
        logit(e, logtype="ERROR")
        sys.exit(1)
    else:
        return curitem

def runScript(script, script_args=''):

    if os.path.isfile(script):
        logit("Running %s %s" % (script, script_args))
        try:
            subprocess.check_call("%s %s" % (script, script_args), shell=True)
        except subprocess.CalledProcessError:
            logit("Command '%s %s' errored out. Exiting program" % (script, script_args), logtype="ERROR")
            sys.exit(1)
        else:
            logit("Command '%s %s' completed without issue." % (script, script_args), logtype="SUCCESS")
    else:
       logit("%s does not exist" % script, logtype="ERROR");

def assignIPs(devicename):

    retvaljson = ""

    if os.path.isfile('./manage-ips.py'):
        logit("Running ./manage-ips.py request-ips --name %s --networks management,overlay,storage" % devicename)
        try:
            retvaljson = subprocess.check_output(['./manage-ips.py', 'request-ips', '--name', devicename, '--networks', 'management,overlay,storage'])
        except subprocess.CalledProcessError:
            logit("Command './manage-ips.py request-ips --name %s --networks management,overlay,storage' errored out. Exiting program" % devicename, logtype="ERROR")
            sys.exit(1)
        else:
            logit("Command './manage-ips.py request-ips --name %s --networks management,overlay,storage' completed without issue" % devicename, logtype="SUCCESS")
    else:
       logit("%s does not exist" % script, logtype="ERROR");

    retvaldict = json.loads(retvaljson)
    return retvaldict


def libvirtConnect():
    conn = libvirt.open('qemu:///system')
    if conn == None:
        logit("Failed to open connection to the qemu:///system", logtype="ERROR")
        sys.exit(1)

    return conn

def manageNetworks(curconfig):

    management_gw = getConfigItem(curconfig, 'networks', 'management_gw')
    management_netmask = getConfigItem(curconfig, 'networks', 'management_netmask')
    management_network = getConfigItem(curconfig, 'networks', 'management_network')
    runScript('./manage-ips.py', 'allocate-network --name management --cidr %s/%s --gateway %s' % (management_network, management_netmask, management_gw));

    overlay_gw = getConfigItem(curconfig, 'networks', 'overlay_gw')
    overlay_netmask = getConfigItem(curconfig, 'networks', 'overlay_netmask')
    overlay_network = getConfigItem(curconfig, 'networks', 'overlay_network')
    runScript('./manage-ips.py', 'allocate-network --name overlay --cidr %s/%s --gateway %s' % (overlay_network, overlay_netmask, overlay_gw));

    storage_gw = getConfigItem(curconfig, 'networks', 'storage_gw')
    storage_netmask = getConfigItem(curconfig, 'networks', 'storage_netmask')
    storage_network = getConfigItem(curconfig, 'networks', 'storage_network')
    runScript('./manage-ips.py', 'allocate-network --name storage --cidr %s/%s --gateway %s' % (storage_network, storage_netmask, storage_gw));
    

def configureNetworks(curconfig):
    conn = libvirtConnect()   

    found_storage = 0
    found_overlay = 0
    found_management = 0

    # Remove the default network if it exists
    networks = conn.listNetworks()
    for network in networks:
        if network == 'default':
            netobj = conn.networkLookupByName('default')
            netobj.destroy()
            netobj.undefine()
        if network == 'storage':
            found_storage = 1;
        if network == 'management':
            found_management = 1;
        if network == 'overlay':
            found_overlay = 1;


    # Create a management network with external access
    management_gw = getConfigItem(curconfig, 'networks', 'management_gw')
    management_netmask = getConfigItem(curconfig, 'networks', 'management_netmask')
    if found_management == 0:
        logit("Creating management network", logtype="ACTION")
        management_net_xml = """<network>
  <name>management</name>
  <uuid>%s</uuid>
  <forward mode='nat'/>
  <bridge name='virbr0' stp='on' delay='0'/>
  <ip address='%s' netmask='%s'>
  </ip>
</network> """ % (uuid.uuid4(), management_gw, management_netmask)

        # Define it in libvirt
        netobj = conn.networkDefineXML(management_net_xml)
        if netobj == None:
            logit("Failed to create management network", logtype="ERROR")
            sys.exit(1)

        # Set it to autostart
        netobj.setAutostart(1)
        
        # Make it active
        isactive = netobj.isActive()
        if isactive == 1:
            logit("Network management is up and active", logtype="SUCCESS")
        else:
            netobj.create()

    # Create a overlay network
    overlay_gw = getConfigItem(curconfig, 'networks', 'overlay_gw')
    overlay_netmask = getConfigItem(curconfig, 'networks', 'overlay_netmask')
    if found_overlay == 0:
        logit("Creating overlay network", logtype="ACTION")
        overlay_net_xml = """<network>
  <name>overlay</name>
  <uuid>%s</uuid>
  <bridge name='virbr1' stp='on' delay='0'/>
  <ip address='%s' netmask='%s'>
  </ip>
</network> """ % (uuid.uuid4(), overlay_gw, overlay_netmask)

        # Define it in libvirt
        netobj = conn.networkDefineXML(overlay_net_xml)
        if netobj == None:
            logit("Failed to create overlay network", logtype="ERROR")
            sys.exit(1)

        # Set it to autostart
        netobj.setAutostart(1)
        
        # Make it active
        isactive = netobj.isActive()
        if isactive == 1:
            logit("Network overlay is up and active", logtype="SUCCESS")
        else:
            netobj.create()

    # Create a storage network
    storage_gw = getConfigItem(curconfig, 'networks', 'storage_gw')
    storage_netmask = getConfigItem(curconfig, 'networks', 'storage_netmask')
    if found_storage == 0:
        logit("Creating storage network", logtype="ACTION")
        storage_net_xml = """<network>
  <name>storage</name>
  <uuid>%s</uuid>
  <bridge name='virbr2' stp='on' delay='0'/>
  <ip address='%s' netmask='%s'>
  </ip>
</network> """ % (uuid.uuid4(), storage_gw, storage_netmask)

        # Define it in libvirt
        netobj = conn.networkDefineXML(storage_net_xml)
        if netobj == None:
            logit("Failed to create storage network", logtype="ERROR")
            sys.exit(1)

        # Set it to autostart
        netobj.setAutostart(1)
        
        # Make it active
        isactive = netobj.isActive()
        if isactive == 1:
            logit("Network storage is up and active", logtype="SUCCESS")
        else:
            netobj.create()


def destroyNetworks():

    conn = libvirtConnect()   

    # Remove the default network if it exists
    networks = conn.listNetworks()
    for network in networks:
        if network in ['default', 'storage', 'management', 'overlay']:
            logit("Deleting %s network" % network, logtype="ACTION")
            netobj = conn.networkLookupByName(network)
            netobj.destroy()
            netobj.undefine()

def updateHostsFile(curip, curhostname):
    hostsfile = open('/etc/hosts', 'r')
    hostfound = 0
    for hostsline in hostsfile:
        hostentry = "%s %s" % (curip, curhostname)
        if hostentry in hostsline:
            logit('%s alredy exists in /etc/hosts' % hostentry)
            hostfound = 1
    hostsfile.close()

    hostsfile = open('/etc/hosts', 'a')
    if hostfound != 1:
        logit('writing "%s" to /etc/hosts' % hostentry, logtype="ACTION")
        hostsfile.write(hostentry + "\n")
    hostsfile.close()
    

  


########################
# Create the deploy box
########################
def createDeployVM(curconfig):

    # Check if deploy device exists
    conn = libvirtConnect()   


    # Create a preseed from a template
    management_gw = getConfigItem(curconfig, 'networks', 'management_gw')
    management_netmask = getConfigItem(curconfig, 'networks', 'management_netmask')
    management_network = getConfigItem(curconfig, 'networks', 'management_network')
    vm_gecos = getConfigItem(curconfig, 'default', 'vm_gecos')
    vm_username = getConfigItem(curconfig, 'default', 'vm_username')
    vm_password = getConfigItem(curconfig, 'default', 'vm_password')
    ipinfo = assignIPs('deploy')
    templateinfo = {
        'ipaddress': ipinfo['management'],
        'netmask': management_netmask,
        'gateway': management_gw,
        'nameservers': management_gw,
        'vm_password': vm_password,
        'vm_username': vm_username,
        'vm_gecos': vm_gecos
    }
    finalpreseed = jinja2.Environment(loader=jinja2.FileSystemLoader('./templates/')).get_template('preseed.cfg.j2').render(templateinfo)
    prfile = open('./files/preseed.cfg', 'w')
    prfile.write(finalpreseed)
    prfile.close()

    # Lets go ahead and add the management ip to the local /etc/hosts file
    updateHostsFile(ipinfo['management'], 'deploy')

    # Just log and return if it already exists
    domainids = conn.listDomainsID()
    for domainid in domainids:
        domainobj = conn.lookupByID(domainid)
        domain = "%s" % domainobj.name()
        if domain == 'deploy':
            logit("Deploy vm already exists.", logtype="INFO")
            return 0

    
    # Create the libvirt command(we are using virt-install as it allows initrd injection)
    virt_install_command = "virt-install --connect qemu:///system --nographics --noautoconsole --wait -1 " \
                           "--name %s " \
                           "--ram %s " \
                           "--disk %s " \
                           "--location %s " \
                           "--initrd-inject %s " \
                           "--extra-args %s " \
                           "--os-type %s " \
                           "--os-variant %s " \
                           "--virt-type %s " \
        % (
            getConfigItem(curconfig, 'deploy', 'virt_install_name'),
            getConfigItem(curconfig, 'deploy', 'virt_install_ram'),
            getConfigItem(curconfig, 'deploy', 'virt_install_disk'),
            getConfigItem(curconfig, 'deploy', 'virt_install_location'),
            getConfigItem(curconfig, 'deploy', 'virt_install_initrd-inject'),
            getConfigItem(curconfig, 'deploy', 'virt_install_extra-args'),
            getConfigItem(curconfig, 'deploy', 'virt_install_os-type'),
            getConfigItem(curconfig, 'deploy', 'virt_install_os-variant'),
            getConfigItem(curconfig, 'deploy', 'virt_install_virt-type')
        )
    network_string = getConfigItem(curconfig, 'deploy', 'virt_install_networks')
    network_string = network_string.strip('"')
    for network in network_string.split(" "):
        virt_install_command = virt_install_command + "--network %s " % network

    # Build the server over the networking using virt-install
    logit("Running virt-install to create the deploy device.", logtype="ACTION")
    logit("Run 'clear; virsh console deploy' in a separate window to watch.")
    try:
        subprocess.check_call(virt_install_command, shell=True)
    except subprocess.CalledProcessError:
        logit("virt-install command errored out. Exiting program", logtype="ERROR")
        sys.exit(1)
    else:
        logit("virt-install completed without issue.", logtype="SUCCESS")




#########################
# Destroy the Deploy VM
#########################
def destroyDeployVM(curconfig):

    # Check if deploy device exists
    conn = libvirtConnect()   

    # Just log and return if it already exists
    domainids = conn.listDomainsID()
    for domainid in domainids:
        domainobj = conn.lookupByID(domainid)
        domain = "%s" % domainobj.name()
        if domain == 'deploy':
            logit("Deploy VM Found. Destroying", logtype="ACTION")
            domainobj.destroy()
            domainobj.undefine()
            return 0



################################
# Create the lab environment
################################
def create_func(curconfig):

    # Pull some variables out of the config
    scripts_dir = getConfigItem(curconfig, 'default', 'scripts-dir')

    # Run script to prepar host for kvm usage
    runScript("%s/install_virtual_tools.sh" % scripts_dir)


    # Run script to set up storage
    image_disk = getConfigItem(curconfig, 'lab-host', 'lab-disk')
    runScript("%s/create_image_disk.sh" % scripts_dir, image_disk)

    # Add networks to managment db
    manageNetworks(curconfig)

    # Set up Networing
    configureNetworks(curconfig)

    # Create the deploy device
    createDeployVM(curconfig)

    # Copy the root public key over
    deployRootKey('deploy', 'openstack', 'openstack')

    

    

###############################
# Destroy the lab environment
###############################
def destroy_func(curconfig):

    # Destroy the deploy device
    destroyDeployVM(curconfig)

    # Clean Networking
    destroyNetworks()

    # Pull some variables out of the config
    scripts_dir = getConfigItem(curconfig, 'default', 'scripts-dir')

    # Run script to destroy storage
    image_disk = getConfigItem(curconfig, 'lab-host', 'lab-disk')
    runScript("%s/destroy_image_disk.sh" % scripts_dir, image_disk)


def main():

    ######################
    # Parse the arguments
    ######################
    parser = argparse.ArgumentParser(description='Script to assist in creating and setting up openstack lab environments.')
    subparsers = parser.add_subparsers(help='subcommands create|destroy')

    parser_create = subparsers.add_parser('create', help='create the lab')
    parser_create.set_defaults(func='create') 

    parser_destroy = subparsers.add_parser('destroy', help='destroy the lab')
    parser_destroy.set_defaults(func='destroy') 

    args = parser.parse_args()


    #############################
    # Get the configuration 
    #############################
    config_loc = ['./lab-config.ini', './etc/lab-config/lab-config.ini' , '/etc/lab-config/lab-config.ini']
    config_file = ''
    for cfg_loc in config_loc:
        if os.path.isfile(cfg_loc):
            config_file = cfg_loc 
            break
    if config_file != '':
        logit("Parsing config file %s" % config_file)
        config = configparser.ConfigParser()
        config.read(config_file)
    else:
        logit("Could not find lab-config.ini", logtype="ERROR")
        sys.exit(1)


    if args.func == 'destroy':
        destroy_func(config)
 
    if args.func == 'create':
        create_func(config)

  
 
        
      

    




if __name__ == '__main__':
  main()
