#!/bin/bash

# Allow it to be called from within or a directory back
for FUNCTIONFILE in functions scripts/functions
do
  if [ -e "$FUNCTIONFILE" ]
  then
    . "$FUNCTIONFILE"
  fi
done


# Pull arguments
if [ $# -ne 1 ]
then
  echo "Usage: prep_image_disk.sh" 
  exit 1
else
  CURDISK=$1
fi

VGNAME="labvg00"
LVNAME="lablv00"


# UnMount /var/lib/libvirt/images
mount | grep  "/var/lib/libvirt/images" > /dev/null 2>&1
if [ $? != 0 ]
then
  loginfo "/dev/mapper/${VGNAME}-${LVNAME} is already unmounted from /var/lib/libvirt/images"
else
  logaction "umount /var/lib/libvirt/images"
  umount /var/lib/libvirt/images
  if [ $? != 0 ]
  then
    logerr "UnMounting /var/lib/libvirt/images failed"
    exit 1
  fi
fi

# Remove the mount point to the /etc/fstab file
grep "/dev/mapper/${VGNAME}-${LVNAME}" /etc/fstab > /dev/null 2>&1
if [ $? != 0 ]
then
  loginfo "/dev/mapper/${VGNAME}-${LVNAME} is already removed from the fstab file"
else
  logaction "sed -i.bak	'/\/var\/lib\/libvirt\/images/d' /etc/fstab"
  sed -i.bak '/\/var\/lib\/libvirt\/images/d' /etc/fstab > /dev/null 2>&1
  grep "/dev/mapper/${VGNAME}-${LVNAME}" /etc/fstab > /dev/null 2>&1
  if [ $? == 0 ]
  then
    logerr "Removing the /var/lib/libvirt/images line from fstab failed"
    exit 1
  fi
fi

# Set up the logical volume if needed
lvdisplay ${VGNAME}/${LVNAME} > /dev/null 2>&1
if [ $? != 0 ]
then
  loginfo "Logical volume $LVNAME has already been removed"
else
  logaction "lvremove -y ${VGNAME}/${LVNAME}"
  lvremove -y ${VGNAME}/${LVNAME} > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "lvremove -y ${VGNAME}/${LVNAME} failed"
    exit 1
  fi
fi

# Set up the lvm volume group if needed
vgck $VGNAME > /dev/null 2>&1
if [ $? != 0 ]
then
  loginfo "Volume Group $VGNAME already destroyed"
else
  logaction "vgremove $VGNAME"
  vgremove $VGNAME > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "vgremove $VGNAME failed"
    exit 1
  fi
fi


echo $CURDISK | egrep '[0-9]$' > /dev/null 2>&1
if [ $? != 0 ]
then
  PCURDISK="${CURDISK}1"
else
  PCURDISK="${CURDISK}"
fi


# Set up physical volume if needed
pvck $PCURDISK > /dev/null 2>&1
if [ $? != 0 ]
then
  loginfo "${PCURDISK} is already wiped of the physical volume data"
else
  logaction "pvremove $PCURDISK"
  pvremove $PCURDISK  > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "pvremove $PCURDISK failed"
    exit 1
  fi
fi


# Create a partiton if the device doesn't already end in a numeral
if [ -e "$PCURDISK" ]
then
  loginfo "Removing partition $PCURDISK"
  logaction "parted --script ${CURDISK} rm 1"
  parted --script ${CURDISK} rm 1 > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "removing partion from ${CURDISK} failed"
  fi
else
  loginfo "Partition $PCURDISK already removed"
fi










