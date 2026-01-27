#!/bin/sh

echo "Current edids:"
find /sys/devices -name "edid"
echo Giving dGPU to VM
sleep 2 # TODO remove this
modprobe vfio-pci
systemctl stop display-manager.service
sleep 10
modprobe -r amdgpu
modprobe -r snd_hda_intel
sleep 10 # TODO fix this
echo vfio-pci > /sys/bus/pci/devices/0000\:03\:00.0/driver_override
echo vfio-pci > /sys/bus/pci/devices/0000\:03\:00.1/driver_override
sleep 1
echo Load drivers
modprobe snd_hda_intel
modprobe amdgpu
sleep 1
#systemctl start display-manager.service
#sleep 5
echo Bar 1
echo 14 > /sys/bus/pci/devices/0000\:03\:00.0/resource0_resize
echo Bar 2
echo 8 > /sys/bus/pci/devices/0000\:03\:00.0/resource2_resize
sleep 5
echo 1002 744c > /sys/bus/pci/drivers/vfio-pci/new_id
echo "Video new_id result: $?"
echo 1002 ab30 > /sys/bus/pci/drivers/vfio-pci/new_id
echo "Audio new_id result: $?"
sleep 15
#systemctl start display-manager.service

# https://stackoverflow.com/questions/61558734/vfio-00004100-0-failed-to-open-dev-vfio-32-no-such-file-or-directory-qemu

# echo > /sys/bus/pci/devices/$VIDEO_DEVICE/driver_override

# echo "0000:03:00.0" > /sys/bus/pci/drivers/vfio-pci/unbind
# echo "0000:03:00.1" > /sys/bus/pci/drivers/vfio-pci/unbind

# lscpi -nn for vendor and device id
# lspci -vvvs 00:03:00.0 | grep BAR

# https://angrysysadmins.tech/index.php/2023/08/grassyloki/vfio-how-to-enable-resizeable-bar-rebar-in-your-vfio-virtual-machine/
# 1 = 2MB
# 2 = 4MB
# 3 = 8MB
# 4 = 16MB
# 5 = 32MB
# 6 = 64MB
# 7 = 128MB
# 8 = 256MB
# 9 = 512MB
# 10 = 1GB
# 11 = 2GB
# 12 = 4GB
# 13 = 8GB
# 14 = 16GB
# 15 = 32GB
