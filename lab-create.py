#!/usr/bin/python

import os
import sys
import argparse
import subprocess
import configparser

# apt-get install python-configparsesr python-lvm2

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
    runScript("%s/prep_image_disk.sh" % scripts_dir, image_disk)



def destroy_func(curconfig):
  print ""


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

    #print args  

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
