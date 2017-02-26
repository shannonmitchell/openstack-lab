#!/usr/bin/python

import os
import sys
import uuid
import libvirt
import argparse
import subprocess
import configparser

# apt-get install python-configparsesr python-lvm2 python-libvirt

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

def libvirtConnect():
    conn = libvirt.open('qemu:///system')
    if conn == None:
        logit("Failed to open connection to the qemu:///system", logtype="ERROR")
        sys.exit(1)

    return conn

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







def create_func(curconfig):

    ########################################
    # Pull some variables out of the config
    ########################################
    scripts_dir = getConfigItem(curconfig, 'default', 'scripts-dir')

    ###########################################
    # Run script to prepar host for kvm usage
    ###########################################
    runScript("%s/install_virtual_tools.sh" % scripts_dir)


    ################################
    # Run script to set up storage
    ################################
    image_disk = getConfigItem(curconfig, 'lab-host', 'lab-disk')
    runScript("%s/create_image_disk.sh" % scripts_dir, image_disk)

    ###################
    # Set up Networing
    ###################
    configureNetworks(curconfig)


    

    



def destroy_func(curconfig):

    ###################
    # Clean Networking
    ###################
    destroyNetworks()

    ########################################
    # Pull some variables out of the config
    ########################################
    scripts_dir = getConfigItem(curconfig, 'default', 'scripts-dir')

    ################################
    # Run script to destroy storage
    ################################
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
    config_loc = ['./lab-config.ini', './etc/lab-config.ini' , '/etc/lab-config.ini']
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
