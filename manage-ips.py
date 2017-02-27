#!/usr/bin/python

import argparse
import ipaddress


#apt-get install python-ipaddress

def allocateNetwork(netname, netcidr):
    print 'allocating network: %s => %s' % (netname, netcidr)

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
    parser_list.set_defaults(func='list-networks')


    args = parser.parse_args()

    # Allocate a new network
    if args.func == 'allocate-network':
        allocateNetwork(args.name, args.cidr)


if __name__ == '__main__':
    main()
