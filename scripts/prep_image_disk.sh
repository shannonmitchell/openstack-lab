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


# Create a partiton if the device doesn't already end in a numeral
echo $CURDISK | egrep '[0-9]$' > /dev/null 2>&1
if [ $? != 0 ]
then
  PCURDISK="${CURDISK}1"
  if [ ! -e "$PCURDISK" ]
  then
    loginfo "Creating partition on $CURDISK"
    logaction "parted --script ${CURDISK} mklabel gpt"
    parted --script ${CURDISK} mklabel gpt > /dev/null 2>&1
    if [ $? != 0 ]
    then
      logerr "parted failed"
    fi
    logaction "parted --align optimal --script ${CURDISK} mkpart primary 0% 100%"
    parted --align optimal --script ${CURDISK} mkpart primary 0% 100% >/dev/null 2>&1
    if [ $? != 0 ]
    then
      logerr "parted failed"
    fi
    logaction "parted ${CURDISK} set 1 lvm on"
    parted ${CURDISK} set 1 lvm on >/dev/null 2>&1
    if [ $? != 0 ]
    then
      logerr "parted failed"
    fi
  else
    loginfo "Partition $PCURDISK already exists"
  fi
  CURDISK="${PCURDISK}"
fi


# Set up physical volume if needed
pvck $CURDISK > /dev/null 2>&1
if [ $? == 0 ]
then
  loginfo "${CURDISK} is already set up as a physical volume"
else
  logaction "pvcreate $CURDISK"
  pvcreate $CURDISK  > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "pvcreate $CURDISK failed"
    exit 1
  fi
fi

# Set up the lvm volume group if needed
vgck $VGNAME > /dev/null 2>&1
if [ $? == 0 ]
then
  loginfo "Volume Group $VGNAME already exists"
else
  logaction "vgcreate $VGNAME $CURDISK"
  vgcreate $VGNAME $CURDISK  > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "vgcreate $VGNAME $CURDISK failed"
    exit 1
  fi
fi

# Set up the logical volume if needed
lvdisplay ${VGNAME}/${LVNAME} > /dev/null 2>&1
if [ $? == 0 ]
then
  loginfo "Logical volume $LVNAME already exists"
else
  logaction "lvcreate -y $VGNAME --name $LVNAME -l +100%FREE"
  lvcreate -y $VGNAME --name $LVNAME -l +100%FREE > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "lvcreate -y $VGNAME --name $LVNAME -l +100%FREE failed"
    exit 1
  fi
fi

# Create a filesystem for it
blkid /dev/mapper/${VGNAME}-${LVNAME} >/dev/nul 2>&1
if [ $? == 0 ]
then
  loginfo "/dev/mapper/${VGNAME}-${LVNAME} already has a filesystem on it"
else
  logaction "mkfs.ext4 /dev/mapper/${VGNAME}-${LVNAME}"
  mkfs.ext4 /dev/mapper/${VGNAME}-${LVNAME} > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logerr "mkfs.ext4 /dev/mapper/${VGNAME}-${LVNAME} failed"
    exit 1
  fi
fi
