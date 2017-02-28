#!/usr/bin/python

import os
import sys
import json
import argparse
import ipaddress
import configparser


#apt-get install python-ipaddress

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

def saveNetwork(data_path, net_data):

    savefile = open("%s/networks/%s.json" % (data_path, net_data['network_name']), 'w')
    jsondata = json.dumps(net_data)
    savefile.write(jsondata) 
    savefile.close()

def getNetwork(data_path, net_data):

    savefile = open("%s/networks/%s.json" % (data_path, net_data['network_name']), 'w')
    jsondata = json.dumps(net_data)
    savefile.write(jsondata) 
    savefile.close()


def checkDataPathDirs(data_path):

        if not os.path.exists("%s/networks" % data_path):
            os.makedirs("%s/networks" % data_path)
  
def allocateNetwork(data_path, netname, netcidr, gateway):

    # Check that a network by that name doesn't already exist.
    if os.path.exists("%s/networks/%s.json" % (data_path, netname)):
        logit("Network by the name of %s is already defined" % netname, logtype="ERROR")
        return 1

    # Convert data to json and save.
    try:
        newnetwork = ipaddress.ip_network(unicode(netcidr))
        savenet = {}
        savenet['network_name'] = netname
        savenet['network_cidr'] = netcidr
        savenet['network_broadcast'] = str(newnetwork[-1])
        savenet['reserved_ips'] = []
        savenet['reserved_ips'].append(str(newnetwork[0]))
        savenet['reserved_ips'].append(str(newnetwork[-1]))
        savenet['mappings'] = {}
        print gateway
        if gateway == '' or gateway == None:
            savenet['network_gateway'] = str(newnetwork[1])
            savenet['reserved_ips'].append(str(newnetwork[1]))
        else: 
            savenet['network_gateway'] = gateway
            savenet['reserved_ips'].append(gateway)

        saveNetwork(data_path, savenet)

    except ipaddress.AddressValueError, e:
        logit("Error while defining network %s: %s" % (netcidr, e), logtype="ERROR")
    except ipaddress.NetmaskValueError, e:
        logit("Error while defining network %s: %s" % (netcidr, e), logtype="ERROR")


def listNetworks(data_path, showmaps):
    
    net_loc = "%s/networks/" % data_path
    for curfile in os.listdir(net_loc):
        if curfile.endswith('.json'):
            rfile = open("%s/%s" % (net_loc, curfile), 'r')
            json_data = rfile.read()
            data_dict = json.loads(json_data)
            rfile.close()
            print "%-20s %-20s %-10s" % (data_dict['network_name'] + ':', 'cidr(' + data_dict['network_cidr'] + ')', 'gw(' + data_dict['network_gateway'] + ')')
            if showmaps:
                print
                for mapping in data_dict['mappings']:
                    print "    %-10s => %-10s" % (mapping, data_dict['mappings'][mapping])
                print
            
        
def removeNetwork(data_path, netname):

    # Check that a network by that name doesn't already exist.
    if not os.path.exists("%s/networks/%s.json" % (data_path, netname)):
        logit("Network by the name of %s does not exist" % netname, logtype="ERROR")
        return 1

    # Delete it
    os.unlink("%s/networks/%s.json" % (data_path, netname))


def requestIPs(data_path, devname, networks):

    networkarr = networks.split(',')
    retval = {}

    net_loc = "%s/networks/" % data_path
    for curfile in os.listdir(net_loc):
        if curfile.endswith('.json'):
            rfile = open("%s/%s" % (net_loc, curfile), 'r')
            json_data = rfile.read()
            data_dict = json.loads(json_data)
            rfile.close()
            if data_dict['network_name'] in networkarr:

                # Check to see if a mapping exists and add to return value
                preassigned = 0
                for mapping in data_dict['mappings']:
                    if mapping == devname:
                        retval[data_dict['network_name']] = data_dict['mappings'][mapping]
                        preassigned = 1
                        break

                # If already assigned skip 
                if preassigned == 1:
                    continue

                # Nothing was found.  Get a list of used ip addresses.
                used_ips = data_dict['reserved_ips'][:]
                for mapping in data_dict['mappings']:
                    used_ips.append(data_dict['mappings'][mapping])

                # Look for a non-used ip and assign it
                curnet = ipaddress.ip_network(unicode(data_dict['network_cidr']))
                for curip in curnet:
                    if str(curip) not in used_ips:
                        data_dict['mappings'][devname] = str(curip)
                        retval[data_dict['network_name']] = str(curip)
                        break

            # Save the changes before looping through the next network.
            saveNetwork(data_path, data_dict)

    # Print the results in json format 
    print json.dumps(retval)

    return 0


def main():

    ######################
    # Parse the arguments
    ######################
    parser = argparse.ArgumentParser(description='Script to assist in managing networks and ips.')
    subparsers = parser.add_subparsers(help='subcommands allocate-network|remove-network')

    parser_allocate = subparsers.add_parser('allocate-network', help='Allocate a new network')
    parser_allocate.set_defaults(func='allocate-network')
    parser_allocate.add_argument('--name', required=True, help="alphanumeric name of your network. No spaces.");
    parser_allocate.add_argument('--cidr', required=True, help="ex: 192.168.0.0/24");
    parser_allocate.add_argument('--gateway', required=False, help="Will default to the 1st ip. ex: 192.168.0.1");

    parser_remove = subparsers.add_parser('remove-network', help='Remove a network')
    parser_remove.set_defaults(func='remove-network')
    parser_remove.add_argument('--name', required=True, help="alphanumeric name of your network.");

    parser_list = subparsers.add_parser('list-networks', help='List defined networks')
    parser_list.add_argument('--show-mappings', dest='maps', action='store_true', help="Show mappings along with each network.");
    parser_list.set_defaults(func='list-networks')

    parser_requestips = subparsers.add_parser('request-ips', help='Request ip addresses from available networks for a device')
    parser_requestips.set_defaults(func='request-ips')
    parser_requestips.add_argument('--name', required=True, help="Name of the device requesing the ip addresses.");
    parser_requestips.add_argument('--networks', required=True, help="Comma separated list of networks to request ip addresess from. If already assigned, the same ip will be returned.");


    args = parser.parse_args()


    #############################
    # Get the configuration 
    #############################
    config_loc = ['./manage-ips.conf', './etc/manage-ips/manage-ips.conf' , '/etc/manage-ips/manage-ips.conf']
    config_file = ''
    for cfg_loc in config_loc:
        if os.path.isfile(cfg_loc):
            config_file = cfg_loc
            break
    if config_file != '':
        config = configparser.ConfigParser()
        config.read(config_file)
    else:
        logit("Could not find manage-ips.ini", logtype="ERROR")
        sys.exit(1)

    data_path = getConfigItem(config, 'default', 'data_path')


    ###############################
    # Make sure ip data dirs exist
    ###############################
    checkDataPathDirs(data_path)


    ###############################
    # Allocate a new network
    ###############################
    if args.func == 'allocate-network':
        allocateNetwork(data_path, args.name, args.cidr, args.gateway)


    ###############################
    # List networks
    ###############################
    if args.func == 'list-networks':
        listNetworks(data_path, args.maps)

    ###############################
    # Delete a network
    ###############################
    if args.func == 'remove-network':
        removeNetwork(data_path, args.name)

    ###############################
    # Request device ip addresses
    ###############################
    if args.func == 'request-ips':
        requestIPs(data_path, args.name, args.networks)


if __name__ == '__main__':
    main()
