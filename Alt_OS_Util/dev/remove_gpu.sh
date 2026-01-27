#!/bin/sh

BRIDGE_PORT="0000:02:00.0"

echo Taking back dGPU from VM
sleep 2 # TODO remove this
systemctl stop display-manager.service
sleep 10
echo "0000:03:00.0" > /sys/bus/pci/drivers/vfio-pci/unbind
echo "0000:03:00.1" > /sys/bus/pci/drivers/vfio-pci/unbind
sleep 3
echo > /sys/bus/pci/devices/0000\:03\:00.0/driver_override
echo > /sys/bus/pci/devices/0000\:03\:00.1/driver_override
sleep 3
echo "1" > /sys/bus/pci/devices/0000\:03\:00.0/remove
echo "1" > /sys/bus/pci/devices/0000\:03\:00.1/remove
echo "dGPU removed, about to remove driver for iGPU"
sleep 3
echo "before modprobe remove"
modprobe -r vfio-pci
modprobe -r amdgpu
modprobe -r snd_hda_intel
echo "after modprobe remove"
sleep 3
# echo "doing hot reset"
# reg=$(setpci -s $BRIDGE_PORT BRIDGE_CONTROL)
# echo "reg = $reg"
# setpci -s $BRIDGE_PORT BRIDGE_CONTROL=$(printf "%04x" $(("0x$reg" | 0x40)))
# sleep 0.1
# setpci -s $BRIDGE_PORT BRIDGE_CONTROL=$reg
# echo "doing sysfs reset"
# echo "1" > /sys/bus/pci/devices/0000\:02\:00.0/reset
# sleep 5
echo "before rescan"
echo "1" > /sys/bus/pci/rescan
echo "after rescan"
sleep 3
echo "before modprobe add"
modprobe snd_hda_intel
modprobe amdgpu
echo "after modprobe add"
sleep 1
# systemctl restart display-manager.service
echo "Current edids:"
find /sys/devices -name "edid"
sleep 10
# systemctl start display-manager.service

# TODO need to figure out how to reset dGPU such that it can be re-added to VM w/o errors
