#!/bin/sh

mkdir -p /root/win_test/tpm

swtpm socket --tpmstate dir=/root/win_test/tpm --ctrl type=unixio,path=/root/win_test/tpm/sock --tpm2 --daemon

# TODO remove
# shutdown +3
free -h

qemu-system-x86_64 \
 -M q35 -m 32G \
 -cpu host,hv_time,kvm=off,hv_vendor_id=AMMD,-hypervisor \
 -enable-kvm -smp cores=15,sockets=1,threads=1 \
 -hda /root/win_test/ssd.img \
 -usb -device usb-tablet \
 -device pcie-root-port,id=root0,bus=pcie.0,chassis=1 \
 -device vfio-pci,host=03:00.0,addr=0.0,multifunction=on,bus=root0 \
 -device vfio-pci,host=03:00.1,addr=0.1,bus=root0 \
 -chardev socket,id=chrtpm,path=/root/win_test/tpm/sock \
 -tpmdev emulator,id=tpm0,chardev=chrtpm -device tpm-tis,tpmdev=tpm0 \
 -drive if=pflash,format=raw,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd,read-only=on \
 -drive if=pflash,format=raw,file=/root/win_test/uefi_vars.fd \
 -fw_cfg opt/ovmf/X-PciMmio64Mb,string=65536 \
 -no-reboot \
 -vga std
#  -boot d \



# -audio driver=sdl,model=hda \

# lspci -nn
# qemu-img create -f qcow2 /root/win_test/ssd.img 100G
# cp /usr/share/edk2/x64/OVMF_VARS.fd /root/win_test/uefi_vars.fd



# -blockdev node-name=ssd1,driver=raw,file.driver=host_device,file.filename=/dev/loop0 \


