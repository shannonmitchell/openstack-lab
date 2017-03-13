#!/bin/bash



###########################################################
# Throwing in some simple output/logging functions for now
###########################################################

function logaction {
  echo "[ACTION]: ${1}"
}
function logsuccess {
  echo "[SUCCESS]: ${1}"
}
function logerr {
  echo "[ERROR]: ${1}"
}
function loginfo {
  echo "[INFO]: ${1}"
}



#######################
# Install Dependancies
#######################


# Always run the update
logaction "Running 'apt-get update'"
apt-get update > /dev/null 2>&1

# Install packages only if needed
loginfo "Checking if dependancies are installed"
INSTALLME=""
for PACKAGE in build-essential createrepo apache2 genisoimage libapache2-mod-wsgi python-cheetah python-netaddr python-simplejson python-urlgrabber python-yaml rsync syslinux tftpd-hpa yum-utils python-django git make python-setuptools pxelinux isc-dhcp-server debmirror fence-agents curl
do
  dpkg -s $PACKAGE > /dev/null 2>&1
  if [ $? != 0 ]
  then
    loginfo "Package ${PACKAGE} is not installed" 
    INSTALLME="${INSTALLME} ${PACKAGE}"
  fi
done

if [ "${INSTALLME}" != "" ]
then
    logaction "apt-get install -y ${INSTALLME}"
    apt-get install -y $INSTALLME > /dev/null 2>&1
    if [ $? != 0 ]
    then
      logerr "Failed to install packages ${INSTALLME}"
    else
      logsuccess "Installed packages ${INSTALLME}"
    fi
fi


#############################
# Install the latest Cobbler
#############################

if [ ! -e "/usr/src/cobbler" ]
then
  logaction "Running 'git clone git://github.com/cobbler/cobbler.git' to /usr/src/cobbler"
  cd /usr/src/
  git clone git://github.com/cobbler/cobbler.git
  cd cobbler

  logaction "Checking out the 2.8 release"
  git checkout release28

  logaction "Compiling the install devinstall and webtest"
  make install
  make devinstall
  make webtest

fi


###########################
# Creating needed symlinks
###########################
loginfo "Checking for needed symlinks"
if [ ! -e "/etc/apache2/conf-enabled/cobbler.conf" ]
then
  logaction "ln -s /etc/apache2/conf-available/cobbler.conf /etc/apache2/conf-enabled/cobbler.conf"
  ln -s /etc/apache2/conf-available/cobbler.conf /etc/apache2/conf-enabled/cobbler.conf
fi

if [ ! -e "/var/www/cobbler" ]
then
  logaction "ln -s /srv/www/cobbler /var/www/cobbler"
  ln -s /srv/www/cobbler /var/www/cobbler
fi

if [ ! -e "/usr/lib/python2.7/dist-packages/cobbler" ]
then
  logaction "ln -s /usr/local/lib/python2.7/dist-packages/cobbler /usr/lib/python2.7/dist-packages/cobbler"
  ln -s /usr/local/lib/python2.7/dist-packages/cobbler /usr/lib/python2.7/dist-packages/cobbler
fi

# may not be needed or possibley backwards?
if [ ! -e "/var/lib/tftpboot" ]
then
  logaction "ln -s /srv/tftp /var/lib/tftpboot"
  ln -s /srv/tftp /var/lib/tftpboot
fi



#################################################
# Make sure the content dir is owned by www-data
#################################################
loginfo "Checking ownership of /var/lib/cobbler/webui_sessions"
ls -ld /var/lib/cobbler/webui_sessions | grep www-data > /dev/null 2>&1
if [ $? != 0 ]
then
  logaction "chown www-data /var/lib/cobbler/webui_sessions"
  chown www-data /var/lib/cobbler/webui_sessions
fi


########################
# Enable apache mods
########################
RESTART_HTTPD=0
if [ ! -e "/etc/apache2/mods-enabled/proxy.load" ]
then
  logaction "a2enmod proxy"
  a2enmod proxy >/dev/null 2>&1
  RESTART_HTTPD=1
fi

if [ ! -e "/etc/apache2/mods-enabled/proxy_http.load" ]
then
  logaction "a2enmod proxy_http"
  a2enmod proxy_http >/dev/null 2>&1
  RESTART_HTTPD=1
fi

if [ ! -e "/etc/apache2/mods-enabled/rewrite.load" ]
then
  logaction "a2enmod rewrite"
  a2enmod rewrite >/dev/null 2>&1
  RESTART_HTTPD=1
fi

if [ RESTART_HTTPD == 1 ]
then
  systemctl restart apache2.service
fi



#########################################################
# Fix signature url to allow download from the interwebs
#########################################################

loginfo "Checking if signature_url in /usr/local/lib/python2.7/dist-packages/cobbler/settings.py needs updating"
grep 'signature_url' /usr/local/lib/python2.7/dist-packages/cobbler/settings.py | grep 'http://cobbler.github.io/signatures/latest.json'  > /dev/null 2>&1
if [ $? != 0 ]
then
  logaction "Updating /usr/local/lib/python2.7/dist-packages/cobbler/settings.py to set signature_url to 'http://cobbler.github.io/signatures/latest.json'"
  sed -ie 's|^.*signature_url.*$|    "signature_url"                       : ["http://cobbler.github.io/signatures/latest.json","str"],|g' /usr/local/lib/python2.7/dist-packages/cobbler/settings.py
fi


##########################################################
# Copy over the needed tftp files used in a cobbler sync
##########################################################
loginfo "Checking if tftp files need copied to /usr/lib/syslinux"
if [ ! -e "/usr/lib/syslinux/pxelinux.0" ]
then
  logaction "cp /usr/lib/PXELINUX/pxelinux.0 /usr/lib/syslinux/"
  cp /usr/lib/PXELINUX/pxelinux.0 /usr/lib/syslinux/
fi

if [ ! -e "/usr/lib/syslinux/menu.c32" ]
then
  logaction "cp /usr/lib/syslinux/modules/bios/* /usr/lib/syslinux/"
  cp /usr/lib/syslinux/modules/bios/* /usr/lib/syslinux/
fi


#################################
# Edit some basic config entries
#################################
PRIMARYIP=$(ip route get 1 | head -n 1 | awk '{print $7}')
NEWPASS=$(openssl passwd -1 'openstack')

loginfo "Making sure server is set to pxe interface ip in /etc/cobbler/settings"
egrep '^server: 127.0.0.1' /etc/cobbler/settings > /dev/null 2>&1
if [ $? == 0 ]
then
  logaction "Setting server in /etc/cobbler/settings"
  sed -ie "s/server: 127.0.0.1/server: $PRIMARYIP/g" /etc/cobbler/settings > /dev/null 2>&1
fi

loginfo "Making sure next_server is set to pxe interface ip in /etc/cobbler/settings"
egrep '^next_server: 127.0.0.1' /etc/cobbler/settings > /dev/null 2>&1
if [ $? == 0 ]
then
  logaction "Setting next_server in /etc/cobbler/settings"
  sed -ie "s/next_server: 127.0.0.1/next_server: $PRIMARYIP/g" /etc/cobbler/settings > /dev/null 2>&1
fi

loginfo "Making sure default_password_crypted is updated to 'openstack' in /etc/cobbler/settings"
egrep '^default_password_crypted:' /etc/cobbler/settings | grep 'WvcIcX2t6crBz2onW'> /dev/null 2>&1
if [ $? == 0 ]
then
  logaction "Setting default_password_crypted in /etc/cobbler/settings"
  sed -ie "s/^default_password_crypted.*$/default_password_crypted: \"$NEWPASS\"/g" /etc/cobbler/settings > /dev/null 2>&1
fi


loginfo "Making sure manage_dhcp is enabled in /etc/cobbler/settings"
egrep '^manage_dhcp: 0' /etc/cobbler/settings > /dev/null 2>&1
if [ $? == 0 ]
then
  logaction "Setting manage_dhcp to 1 in /etc/cobbler/settings"
  sed -ie "s/^manage_dhcp.*$/manage_dhcp: 1/g" /etc/cobbler/settings > /dev/null 2>&1
fi




###############################
# Enable and start the services
###############################

for CURSERVICE in cobblerd.service apache2.service
do

  loginfo "Check if ${CURSERVICE} is enabled"
  systemctl is-enabled ${CURSERVICE} > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logaction "systemctl enable ${CURSERVICE} > /dev/null 2>&1"
    systemctl enable ${CURSERVICE} > /dev/null 2>&1
  fi


  loginfo "Make sure the ${CURSERVICE} service is up and running"
  systemctl status ${CURSERVICE} > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logaction "systemctl start ${CURSERVICE} > /dev/null 2>&1"
    systemctl start ${CURSERVICE} > /dev/null 2>&1
  fi
done


###################################
# Run checks, syncs and downloads
###################################

# restart apache2 and cobblerd one more time before running checks and syncs
logaction "restarting apache2 and cobblerd services to make sure it has all the new settings"
systemctl restart apache2.service > /dev/null 2>&1
systemctl restart cobblerd.service > /dev/null 2>&1


logaction 'cobbler get-loaders'
cobbler get-loaders > /dev/null 2>&1

logaction 'cobbler signature update'
cobbler signature update > /dev/null 2>&1

logaction 'running a cobbler check'
cobbler check | grep 'All systems go' > /dev/null 2>&1
if [ $? != 0 ]
then
   
  logerr 'cobbler check failed.  Please fix any issues and re-run'
  cobbler check
  exit 0
fi


logaction 'cobbler sync'
cobbler sync > /dev/null 2>&1



#############################################
# Run some post dhcp config stuff and resync
#############################################

loginfo "Checking for proper interface configuration in /etc/init.d/isc-dhcp-server"
grep 'INTERFACES=""' /etc/default/isc-dhcp-server > /dev/null 2>&1
if [ $? == 0 ]
then
  logaction "sed -i -e 's/INTERFACES=\"\"/INTERFACES=\"ens2\"/g' /etc/default/isc-dhcp-server"
  sed -i -e 's/INTERFACES=""/INTERFACES="ens2"/g' /etc/default/isc-dhcp-server 
  logaction "systemctl restart isc-dhcp-server.service"
  systemctl restart isc-dhcp-server.service
fi


loginfo "Checking dhcp template for new config"
grep '192.168.33.0' /etc/cobbler/dhcp.template > /dev/null 2>&1
if [ $? != 0 ]
then


  logaction "Updating /etc/cobbler/dhcp.template"
  cp /etc/cobbler/dhcp.template /etc/cobbler/dhcp.template.bak
  cat <<EOF > /etc/cobbler/dhcp.template
ddns-update-style interim;

allow booting;
allow bootp;

ignore client-updates;
set vendorclass = option vendor-class-identifier;

option pxe-system-type code 93 = unsigned integer 16;

subnet 192.168.33.0 netmask 255.255.255.0 {
     option routers             192.168.33.1;
     option domain-name-servers 192.168.33.1;
     option subnet-mask         255.255.255.0;
     range dynamic-bootp        192.168.33.100 192.168.33.254;
     default-lease-time         21600;
     max-lease-time             43200;
     next-server                \$next_server;
     class "pxeclients" {
          match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
          if option pxe-system-type = 00:02 {
                  filename "ia64/elilo.efi";
          } else if option pxe-system-type = 00:06 {
                  filename "grub/grub-x86.efi";
          } else if option pxe-system-type = 00:07 {
                  filename "grub/grub-x86_64.efi";
          } else {
                  filename "pxelinux.0";
          }
     }
}
EOF
  logaction "systemctl restart isc-dhcp-server.service"
  systemctl restart isc-dhcp-server.service
  logaction 'cobbler sync'
  cobbler sync > /dev/null 2>&1
fi



################
# Set up Xenial
################

# import the distro
loginfo "Checking to see if the distro even needs an import"
cobbler distro list | grep 'ubuntu-16.04.2' > /dev/null 2>&1
if [ $? != 0 ]
then


  # Download the iso
  loginfo "Getting Xenial distroISO"
  if [ ! -e "/root/ubuntu-16.04.2-server-amd64.iso" ]
  then
    logaction "wget http://releases.ubuntu.com/xenial/ubuntu-16.04.2-server-amd64.iso -O /root/ubuntu-16.04.2-server-amd64.iso > /dev/null 2>&1"
    wget http://releases.ubuntu.com/xenial/ubuntu-16.04.2-server-amd64.iso -O /root/ubuntu-16.04.2-server-amd64.iso > /dev/null 2>&1
  fi


  # Check the md5 sum
  LOCMD5SUM=$(md5sum /root/ubuntu-16.04.2-server-amd64.iso | awk '{print $1}')
  REMMD5SUM=$(curl http://releases.ubuntu.com/xenial/MD5SUMS -s | grep ubuntu-16.04.2-server-amd64.iso | awk '{print $1}')
  if [ "$LOCMD5SUM" != "$REMMD5SUM" ]
  then
    logerr "md5 sum mispatch between 'md5sum /root/ubuntu-16.04.2-server-amd64.iso' and 'curl http://releases.ubuntu.com/xenial/MD5SUMS -s | grep ubuntu-16.04.2-server-amd64.iso'"
    exit 1
  fi


  # Make a temporary mount for cobbler import
  loginfo "Checking of /root/mnt exists"
  if [ ! -e "/root/mnt" ]
  then
    logaction "mkdir /root/mnt"
    mkdir /root/mnt
  fi

  loginfo "Checking if iso needs mounted"
  mount | grep '/root/mnt' > /dev/null 2<&1
  if [ $? != 0 ]
  then
    logaction "mount -o loop /root/ubuntu-16.04.2-server-amd64.iso  /root/mnt/"
    mount -o loop /root/ubuntu-16.04.2-server-amd64.iso  /root/mnt/ > /dev/null 2>&1
  fi

  # Make sure the signature exists
  loginfo "Making sure Xenial is in the /var/lib/cobbler/distro_signatures.json file"
  grep xenial /var/lib/cobbler/distro_signatures.json > /dev/null 2>&1
  if [ $? != 0 ]
  then

    if [ ! -e "/var/lib/cobbler/distro_signatures.json_orig" ]
    then
      cp /var/lib/cobbler/distro_signatures.json /var/lib/cobbler/distro_signatures.json_orig
    fi
    logaction "adding xenial signature to /var/lib/cobbler/distro_signatures.json"
    sed -i -e 's|^  "ubuntu": {|  "ubuntu": {\n   "xenial": {\n    "signatures":["dists", ".disk"],\n    "version_file":"Release\|mini-info",\n    "version_file_regex":"Codename: xenial\|Ubuntu 16.04",\n    "kernel_arch":"linux-headers-(.*)\\\\.deb",\n    "kernel_arch_regex":null,\n    "supported_arches":["i386","amd64","ppc64el"],\n    "supported_repo_breeds":["apt"],\n    "kernel_file":"(vm)?linux(.*)",\n    "initrd_file":"initrd(.*)\\\\.gz",\n    "isolinux_ok":false,\n    "default_kickstart":"/var/lib/cobbler/kickstarts/sample.seed",\n    "kernel_options":"",\n    "kernel_options_post":"",\n    "boot_files":[],\n    "boot_loaders":{"ppc64el":["grub2"]}\n   },\n|g' /var/lib/cobbler/distro_signatures.json # > /dev/null 2>&1


    logaction "restarting cobblerd services to read in new signatures"
    systemctl restart cobblerd.service > /dev/null 2>&1

    logaction 'cobbler sync'
    cobbler sync > /dev/null 2>&1

  fi


  # test it out
  cobbler signature report --name=ubuntu | grep xenial > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "xenial not found in 'cobbler signature report --name=ubuntu' output"
    exit 1
  fi

  # import the distro
  loginfo "Checking to see if the distro still needs an import"
  cobbler distro list | grep 'ubuntu-16.04.2' > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logaction "cobbler import --breed ubuntu --os-version xenial --name=ubuntu-16.04.2-server-amd64 --path=/root/mnt/"
    cobbler import --breed ubuntu --os-version xenial --name=ubuntu-16.04.2-server-amd64 --path=/root/mnt/ # > /dev/null 2>&1
  fi

  # clean up
  loginfo "Unmounting /root/mnt if mounted"
  mount | grep 'root/mnt' > /dev/null 2>&1
  if [ $? == 0 ]
  then
    logaction 'umount /root/mnt > /dev/null 2>&1'
    umount /root/mnt > /dev/null 2>&1
  fi


  loginfo "Remove iso file if it exists"
  if [ -e '/root/ubuntu-16.04.2-server-amd64.iso' ]
  then
    logaction 'rm /root/ubuntu-16.04.2-server-amd64.iso'
    rm /root/ubuntu-16.04.2-server-amd64.iso
  fi


fi

