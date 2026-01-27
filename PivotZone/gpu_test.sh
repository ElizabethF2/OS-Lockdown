#!/bin/sh
#stat /dev/mapper/tpm_encrypted_root || cryptsetup open /dev/nvme0n1p2 tpm_encrypted_root --key-file /secret.bin
#stat /mnt/secret.bin || mount /dev/mapper/tpm_encrypted_root /mnt
rootdir=/run/PivotZone/backingroot/root
[ -d "$rootdir" ] || rootdir=/root
(
  echo ------------------------------
  echo "rootdir: $rootdir"
  date
  echo depmod
  depmod
  echo "Result: $?"
  sleep 5
  echo remove
  modprobe -r amdgpu
  echo "Result: $?"
  sleep 10
  (cat /proc/kmsg >> $rootdir/gpu_test_kmsg.log 2>&1)&
  echo add back
  modprobe amdgpu
  echo "Result: $?"
  echo dmesg
  busybox dmesg
  echo "Result: $?"
) >> $rootdir/gpu_test.log 2>&1
# ) >> /run/PivotZone/backingroot/root/gpu_test-in-zone.log 2>&1
# ) >> /root/gpu_test-out-of-zone.log 2>&1
# ) >> /mnt/root/gpu_test.log 2>&1
