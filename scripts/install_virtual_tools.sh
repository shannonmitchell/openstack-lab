#!/bin/bash

# Allow it to be called from within or a directory back
for FUNCTIONFILE in functions scripts/functions
do
  if [ -e "$FUNCTIONFILE" ]
  then
    . "$FUNCTIONFILE"
  fi
done

loginfo "If 'apt-get update' hasn't been ran in 12 hours, run it"
# Run 'apt-get update' if it has been 12 hours since the last run
LASTUDATESEC=$[$(date +%s) - $(stat -c %Z /var/lib/apt/periodic/update-success-stamp)]
if [[ "$LASTUPDATESE" > 43200 ]]
then
  logaction "Running 'apt-get update'"
  apt-get update
fi

# Install packages only if needed
for PACKAGE in qemu-kvm libvirt-bin
do
  loginfo "Checking if $PACKAGE is installed"
  dpkg -s $PACKAGE > /dev/null 2>&1
  if [ $? != 0 ]
  then
    logaction "Installing ${PACKAGE}" 
    apt-get install -y $PACKAGE > /dev/null 2>&1
    if [ $? != 0 ]
    then
      logerro "Failed to install package ${PACKAGE}"
    else
      logsuccess "Installed package ${PACKAGE}"
    fi
  fi
done


exit 0
