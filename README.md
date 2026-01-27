# OS Lockdown

This repository contains various utilities related to dual booting, virtualization and security. An overview of the folders in this repository is provided below. See each folder for additional documentation and details.

## AutoTpmEncrypt

This utility enables using a devices TPM to "seal" all of your OS' partitions, boot loader, initramfs, kernel, kernel modules and kernel command line arguments such that the partitions are encrypted and unreadable by other operating systems and tampering with any of them will prevent the system from booting. This effectively makes the encrypted partitions of the sealed OS "erase-only" as it prevents other OS's from reading or writing data in the partitions. This enables dual-booting between an encrypted, trusted OS and a different, untrusted OS while being sure that the untrusted OS cannot modify or read any data from the trusted one. AutoTpmEncrypt supports any Arch Linux based operating system and it includes explicit support for Steam OS and the Steam Deck. Support for other Linux distros will be added in the future and it should be possible to port it to non-Linux OS relatively easily. A [guide](AutoTpmEncrypt/guide.md) is included with detailed steps for using AutoTpmEncrypt on a Steam Deck.


## Windows

This folder contains a set of scripts for removing bloat and telemetry from Windows as well as improving performance and improving the experience of dual booting between Linux and Windows. It also includes scripts which automate switching which OS is booted.


## NVData Tool

NVData Tool is a utility which can be used to dump and modify the nvdata of a device running ChromeOS firmware. nvdata can be used to toggle features such as booting from external devices even when write protection is enabled and, unlike [GBB flags](https://wiki.postmarketos.org/wiki/Category:ChromeOS#GBB_flags), it does not require opening a device to modify it. NVData Tool is designed to be used in conjunction with disk encryption and tamper evident seals to prevent private data from being read from devices with ChromeOS firmware and to make physical attempts to do so conspicuous.


## Alt OS Util

Alt OS Util is a utility which automates switching a GPU between a VM and the host machine. It does this by running as a service which executes early in the boot process and which can claim a GPU for VFIO before it is claimed and initialized by the display manager. Alt OS Util also automates rebooting your device, logging back in and restoring your session. Alt OS Util is designed to assist with using VFIO with GPUs which require a reset via ACPI when switching between different OS's drivers.


## PivotZone

PivotZone is a library and set of utilities for defining, building and managing "pivotzones", in-memory rootfs which the PivotZone library can transition into and out of via pivot_root. Transitioning into a pivotzone enables services to continue running while the device for the rootfs is unmounted and detached from its driver. This can be necessary on systems where a GPU you want to share with a VM via VFIO is on the same IOMMU group as the device containing your rootfs. This enables giving the device to the VM without causing data corruption.
