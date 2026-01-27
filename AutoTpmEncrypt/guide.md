# Steam Deck Secure Dual Booting

This is a guide and a set of scripts designed to walk through setting up [dual booting](https://en.wikipedia.org/wiki/Multi-booting) SteamOS and Windows on a Steam Deck while also enabling [TPM](https://en.wikipedia.org/wiki/Trusted_Platform_Module) based encryption for SteamOS. By using the TPM, it's possible to ensure that your SteamOS partitions can only be decrypted when booting into SteamOS; for any other OS, Windows included, the partitions will just appear as random data so, while Windows could still delete your SteamOS partitions, it cannot read or modify them. If you're a paranoid security nerd but still want to be able to run Windows on your Steam Deck, this is the guide for you!

Note that this setup is overkill for most games. 99.9% of games will run under SteamOS and Linux. Dual booting should be used as a last resort. Bottles ([AppSteam](appstream://com.usebottles.bottles)/[Flathub](https://flathub.org/apps/com.usebottles.bottles)) and Boxes ([AppSteam](appstream://org.gnome.Boxes)/[Flathub](https://flathub.org/apps/org.gnome.Boxes)) are both great apps which can be used to run Windows programs under Linux (and both can be easily installed on SteamOS in desktop mode from the Discover Software Center). Please try them first. For help getting a specific game working under SteamOS and Linux, check [ProtonDB](https://www.protondb.com).

Here be dragons! This is a long, advanced guide which assumes you are very familiar with (or are willing to lookup) how to use Linux's terminal, install Linux, manage partitions, use LUKS, etc. Do not start following this guide if you are not confident in your ability to troubleshoot and resolve any issues that may come up.

Please read or skim through the entire guide before starting. There is an FAQ at the end which includes solutions to common issues.

To follow this guide, you'll need a Steam Deck and a 64 GB or larger micro SD card, though, ideally you'll want a much larger card if you want enough room to install any games. Having a USB hub, keyboard and a second computer with an SD card slot can make the process much easier but are not required.

This guide breaks the process up into four main sections:
  - Installing Windows to your SD card
  - Setting up a second Linux recovery partition on your SD card
  - Using SteamOS to encrypt the recovery partition and the recovery partition to encrypt SteamOS
  - Booting into Windows for the first time and setting up everything there

**Before proceeding, backup any data you care about on your Steam Deck and SD card first!**

## Install Windows

1. Start by downloading a [Windows ISO from Microsoft's website](https://www.microsoft.com/software-download/windows11)

2. Download and extract/setup [Rufus](https://rufus.ie/en). Note that Rufus will only run on Windows. If you do not have a Windows machine on hand, use Boxes and the previously downloaded ISO to create a Windows VM, pass through your SD card and use the VM for all steps involving Rufus. You can also have Rufus [save its output as an uncompressed vhd](https://superuser.com/questions/1489113/getting-rufus-to-output-to-a-disk-image-file) and flash that to your SD card.

3. Rufus will wipe your SD card when installing Windows. Ensure you have backed up any important data on your SD card.

4. Insert your SD card in your Windows machine/vm and run Rufus. Select your SD card from the "Device" dropdown. You may have to check "List USB Hard Drives" under "advanced drive properties" if your SD card is not listed.

5. Use the "SELECT" button under "Boot selection" to pick the Windows ISO you previously downloaded.

6. Ensure "Image option" is "Windows To Go", "Partition scheme" is "GPT" and "Target system" is "UEFI (non CSM)".

7. (Optional) Enter a volume label under "Volume label"

8. Ensure one last time that you selected the right SD card for "Device" and that you have backed up any important data then press "START"

9. Select the edition of Windows you want and click OK

10. Uncheck "Remove requirement for an online Microsoft account"

11. Check "Create a local account with username" and set a username. Also check "Prevent Windows To Go from accessing internal disks" and "Disable data collection (Skip privacy questions)".

12. Click OK. When prompted, confirm one last time that you've picked the correct device before your SD card is wiped then click OK again.

13. Wait for Rufus to finish installing Windows, close Rufus then eject and remove your SD card

Note: SteamOS is still not encrypted at this point so be careful not to boot Windows on it yet

## Setup Recovery Partition

This section will walk you through creating a Linux partition on your SD card. This installation of Linux will be used to encrypt and decrypt SteamOS and it can also be used recover SteamOS if anything makes it unbootable. You may also use this partition to store SteamOS games if you need more storage than your Steam Deck's internal drive offers. The SD card will be split with part of its capacity being given to Windows and the remaining part being given to the recovery partition and SteamOS. Decide what capacity you want each OS to have access to before continuing. Your recovery partition should be at least 4 GB.

1. With the SD card removed, power on your Steam Deck

2. Check for updates using Settings > System > Check For Updates

3. Switch to desktop mode

4. [Set a password for root access](https://help.steampowered.com/en/faqs/view/4FD6-1AD6-CDD5-D31E) if you have not already

5. Insert the SD card

6. Use the partition manager (Application Launcher > System > KDE Partition Manager) to shrink your Windows partition (the ntfs one) to your desired size and fill the freed space with an ext4 partition. This will be your recovery partition.

7. Open a terminal and start a session as root via `sudo su`

7. Use the below commands to mount your recovery partition where /dev/mmcblk0p4 is the partition
```
mkdir ~/tmp_sdlinux_mount
mount /dev/mmcblk0p4 ~/tmp_sdlinux_mount
```

8. Use the below commands to setup a pacman config which will avoid using Valve's Steam Deck servers. Valve's servers do not always contain up to date packages which can cause signature errors during setup.
```
curl https://raw.githubusercontent.com/archlinux/svntogit-packages/packages/pacman/trunk/pacman.conf -o /tmp/defpacman.conf
sed 's/etc\/pacman.d\//tmp\/sdpacmand/' /tmp/defpacman.conf >> /tmp/sdpacman.conf
sed 's/Server = https:\/\/steamdeck/#/' /etc/pacman.d/mirrorlist >> /tmp/sdpacmandmirrorlist
```

9. Use `pacstrap -C /tmp/sdpacman.conf ~/tmp_sdlinux_mount base` to install the base package group

10. Use `genfstab -U ~/tmp_sdlinux_mount >> ~/tmp_sdlinux_mount/etc/fstab` to generate an fstab file then open `~/tmp_sdlinux_mount/etc/fstab` in your editor to verify the fstab file looks correct and to make any additional changes if needed.

11. Use `arch-chroot ~/tmp_sdlinux_mount` to chroot into the recovery partition

12. Set the time zone via `ln -sf /usr/share/zoneinfo/Region/City /etc/localtime` replacing `Region/City` with your actual region and city

13. Uncomment your required locale(s) such as `en_US.UTF-8` in `/etc/locale.gen` then use the command `locale-gen` to generate them. You may use pacman to install your editor of choice.

14. Edit or create `/etc/locale.conf` to replace or add the line `LANG=en_US.UTF-8` where en_US.UTF-8 is your desired locale

15. Edit or create `/etc/vconsole.conf` to replace or add the line `KEYMAP=de-latin1` where de-latin1 is the keymap of your keyboard

16. Edit or create `/etc/hostname` and enter your desired hostname (e.g. `sdlinux`) as its contents

17. Use `passwd` to set your root password

18. Edit `/etc/pacman.d/mirrorlist` to comment out any lines with `steamdeck` or `steamos` in them

19. Use this command to install packages needed for the kernel, gui, networking, etc: `pacman --needed -Syu linux linux-firmware openssh sudo iwd dhcpcd fluxbox xorg xorg-xinit xterm gcc less nano git base-devel grub which python3 lynx`

20. Use `mkdir /efi` and `mount /dev/mmcblk0p1 /efi` where /dev/mmcblk0p1 is your UEFI partition to mount it

21. Use `cp /efi/EFI/Boot/bootx64.efi /efi/EFI/Boot/bootx64.efi.win` to backup the Windows EFI binary

22. Run `grub-install --target=x86_64-efi --efi-directory=/efi --removable --bootloader-id=SD_Grub /dev/mmcblk0` substituting the device for your SD card for /dev/mmcblk0 to generate the EFI binary for the recovery partition

23. Rename the grub binary using `mv /efi/EFI/Boot/bootx64.efi /efi/EFI/Boot/grub.efi`

24. Run `grub-mkconfig -o /boot/grub/grub.cfg`

25. Use the commands below to create a user account and set its password
```
useradd -m deck
usermod -aG wheel deck
passwd deck
```

26. Edit `/etc/sudoers` and uncomment the line that lets members of wheel use sudo

27. Install yay using the commands below
```
cd /tmp
git clone https://aur.archlinux.org/yay.git
chown -R deck:deck yay
cd yay
sudo -u deck makepkg -si
```

28. Use yay to install corekeyboard via `sudo -u deck yay -S corekeyboard`

29. Run `mkdir /etc/systemd/system/getty@tty1.service.d` then create `/etc/systemd/system/getty@tty1.service.d/autologin.conf` with the following contents:
```
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -f -- \\u' --noclear --autologin deck %I $TERM
```

30. Append the below lines to `/home/deck/.bash_profile`:
```
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
  exec startx
fi
```

31. Create `/home/deck/.Xresources` with the below contents
```
*background: rgb:00/00/00
*foreground: rgb:15/4a/21
```

32. Create `/home/deck/.xinitrc` with the following contents:
```
xrandr -o 3
xinput set-prop "FTS3528:00 2808:1015" "Coordinate Transformation Matrix" 0 1 0 -1 0 1 0 0 1
xrdb -load ~/.Xresources
startfluxbox
```

33. Run `sudo -u deck startfluxbox` (ignore the display errors) then edit `/home/deck/.fluxbox/menu` to remove the existing xterm and firefox entries and replace them with:
```
      [exec] (xterm) {xterm -sb}
      [exec] (corekeyboard) {corekeyboard}
```

34. Run `mkdir /var/lib/iwd` then make a file called `/var/lib/iwd/your_ssid.psk` where your_ssid is the ssid of your WiFi network. Put these lines in the file replacing your_passphrase_here with your actual password:
```
[Settings]
AutoConnect=true

[Security]
Passphrase=your_passphrase_here
```

35. Exit out of arch-chroot back to a normal terminal. Then launch the recovery partition in a container with `systemd-nspawn -D ~/tmp_sdlinux_mount`

36. Within the container, run:
```
systemctl enable getty@tty1
systemctl enable iwd.service
systemctl enable dhcpcd.service
```

37. Exit the container back to a normal terminal.

38. Use these commands to cleanup, replacing /dev/mmcblk0p4 with your recovery partition and /dev/mmcblk0p1 with the UEFI partition:
```
umount --all-targets /dev/mmcblk0p1
umount --all-targets /dev/mmcblk0p4
rmdir ~/tmp_sdlinux_mount
```

39. Shutdown your Steam Deck and wait for it to power off completely

40. Boot into the UEFI menu by holding the `Volume Up` button while tapping the `Power` button

41. From the UEFI menu use the D-Pad and A to select Boot From File > Your SD Card (Name Will Vary) > EFI > Boot > grub.efi. Be careful to not bump right on the D-Pad or select any of the Windows EFI binaries.

42. When the Grub menu comes up, press A to continue

43. The Deck should boot into Fluxbox after loading. You can open the Fluxbox menu by right clicking on the desktop. Verify xterm and corekeyboard work as expected. For better readability, consider changing the style via Fluxbox menu > System Styles > Artwiz.

44. Shutdown by tapping the power button. Your recovery partition is now ready for the next section. Congrats on surviving the hardest part of the guide!


## Encrypt SteamOS and Recovery Partition

This section covers encrypting both your original SteamOS partitions and the new recovery partition you just created as well as sealing the encryption keys for the partitions in the Steam Deck's TPM. Most of the work for this section is automated via the auto_tpm_encrypt.py script included with this guide. Read its output carefully and be sure to backup files it tells you to backup to avoid losing access to your files if something goes wrong.

Sealing stores the keys in the TPM and the TPM will only unseal a key for the same OS that was used to seal the key. As a result, each OS must be encrypted in two steps: one to encrypt it and another, once the encrypted OS is booted, to seal its encryption key. Until the keys for both SteamOS and the recovery partition are sealed, the Deck is not secure. Be careful not to accidentally boot into Windows until you have completed this section

1. Power on your Steam Deck and wait for it to boot into SteamOS.

2. Make sure you are on the latest version of SteamOS by selecting Settings > System > Check For Updates

3. Boot into desktop mode

4. Backup anything on your Deck you still haven't backed up.

5. Copy auto_tpm_encrypt.py to your Steam Deck and open a terminal

6. Plug in your Deck. Run `sudo python auto_tpm_encrypt.py`. Keep your Deck plugged in until the script has exited.

7. The script will display some system information. Ensure it is accurate and write down the home, root and var partitions somewhere for later.

8. Select "Encrypt/Decrypt an unbooted partition"

9. When prompted to enter a partition, enter your recovery partition (e.g. `/dev/mmcblk0p4`). You can quickly check what your recovery partition is via Application Launcher > System > KDE Partition Manager

10. Follow the prompts the script gives you until it starts encrypting your partition. Wait while it encrypts the partition. This may take 2+ hours depending on the size of your partition and the speed of your SD card.

11. Once the script finishes, check for any warnings or errors. The script will make a list of backup files it generated. Move or make a copy of these files somewhere you won't lose them. Make sure your backups are copied somewhere off the Steam Deck and the SD card i.e. on another SD card, on another computer, somewhere online, etc.

12. Shutdown SteamOS and boot into your recovery partition using the same process described in the previous section however, this time, use Auto_TPM_Encrypted_Boot.efi rather than grub.efi. Going forward, use Auto_TPM_Encrypted_Boot.efi to boot the recovery partition. grub.efi can only be used to boot the recovery partition when it is decrypted.

13. The boot process will be interrupted by a prompt asking for a passphrase. Press A on your Steam Deck to get past this prompt.

14. If you've unplugged your Deck, plug it back in. From the recovery partition, open a xterm and run `sudo python /root/auto_tpm_encrypt.py`. Keep the deck plugged in until the script has exited.

15. Select "Setup TPM auto-decrypt for the booted OS"

16. Wait a couple of seconds until the script finishes sealing the encryption key for the recovery partition.

17. Shutdown your Deck and wait for it to completely power off.

18. Boot back into your recovery partition. Verify that it does NOT ask for a password this time. Your recovery partition is now encrypted and its key has been sealed in the Deck's TPM. Next we'll do the same for SteamOS.

19. Still in the recovery partition, open xterm and run `sudo python /root/auto_tpm_encrypt.py`. As always, keep the Deck plugged in while the script is running.

20. Select "Encrypt/Decrypt an unbooted partition" and follow the prompts. Use the partitions you took note of in step 7.

21. Wait for the script to encrypt SteamOS. Again, this may take 2+ hours.

22. Check for any warnings or errors. Move or copy the listed backup files somewhere you won't lose them. Again, make sure they are copied somewhere that is not your Steam Deck or the SD card.

23. Shutdown the recovery partition and boot back into SteamOS.

24. When SteamOS boots, you will see 3 password prompts. Press A at each one.

25. From SteamOS, run `sudo python auto_tpm_encrypt.py` and select "Setup TPM auto-decrypt for the booted OS"

26. Follow the prompts to seal the encryption key for SteamOS.

27. Shutdown your Steam Deck.

28. Boot back into SteamOS. Ensure you do not see any password prompts this time and that SteamOS is now encrypted.


## Finish Setting Up Windows

With everything encrypted and sealed, you can now safely boot Windows. This section covers getting Windows setup along with a few tweaks to improve performance, disable telemetry, etc. Unlike other, more drastic tweaks which can be made to Windows, these will leave windows update and the UWP intact so that your Windows install will continue to get security updates and things like Microsoft Store games, Play Anywhere games and Game Pass games will continue to work. If you don't need those, there are further tweaks you can make.

1. Boot into either SteamOS or your recovery partition and run the below commands as root replacing /dev/mmcblk0p1 with the EFI partition on your SD card:
```
mkdir /tmp/sdefi
mount /dev/mmcblk0p1 /tmp/sdefi
mv /tmp/sdefi/EFI/Boot/bootx64.efi.win /tmp/sdefi/EFI/Boot/bootx64.efi
```

2. Shutdown the Deck and wait for it to shutdown completely

3. Enter the Boot Manager by tapping `Power` while holding the `Volume Down` button. Use the D-Pad and A to select your SD card. In the future, you'll use this method to boot into Windows.

4. Complete Windows' [OOBE](https://en.wikipedia.org/wiki/Out-of-box_experience)

5. (Optional) Activate Windows

6. Copy all of the files included in the `Windows` folder to your Windows install. You can do this from SteamOS or from your Windows machine/vm. Your Windows installation will show up in the file manager.

7. Carefully read through winsetup.bat and comment out or modify anything you don't want applied to your Windows install. Cherry-pick what you need and remove what you don't.

8. Run your modified `winsetup.bat`. You will likely be prompted to reboot after some components are installed. Rerun the script after each reboot. The script is designed to be safe to rerun as many times as necessary.

9. If Steam was installed, login to Steam

10. If installing GlosSI, rerun winsetup.bat

11. Let Windows run until it finishes installing all Windows updates and app updates

12. Reboot Windows and ensure everything is working

13. Boot into both SteamOS and your recovery partition to ensure both are still working. If either gives you a password prompt for the encryption passphrase rather than automatically decrypting, Windows may have evicted one of your encryption keys from the TPM when Windows was setting itself up. Use the other, still working OS to reseal the key. For example, if your recovery partition's key was evicted, boot into SteamOS, run `sudo python auto_tpm_encrypt.py`, select "Add blank password to unbooted partition" and follow the prompts to make your recovery partition bootable without a key, then, boot into your recovery partition, run `sudo python /root/auto_tpm_encrypt.py`, and select "Setup TPM auto-decrypt for the booted OS" to reseal the key. If both keys were somehow evicted, you can use your backups from earlier along with a fresh, unencrypted Linux install to add a blank password to both OS.


## Keeping Everything Secure

If you're not already familiar with TPMs, see the question "What exactly is a TPM? How does it work? What's sealing?" in the FAQ.

Now that SteamOS and your recovery partition are encrypted, you can be confident that Windows or any other OS you boot on your Steam Deck will not be able to read or modify any of your encrypted files, however, they can still erase them or replace with another OS. Consider making backups of the ESP binaries auto_tpm_encrypt.py generates (`efi/boot/bootx64.efi` for SteamOS and `EFI/Boot/Auto_TPM_Encrypted_Boot.efi` for the recovery partition) and store them somewhere secure. auto_tpm_encrypt.py seals encryption keys using the [PCRs](https://security.stackexchange.com/questions/252391/understanding-tpm-pcrs-pcr-banks-indexes-and-their-relations) for your Deck's firmware and the current OS' ESP binary so during normal use, SteamOS and your recovery partition should both automatically decrypt and boot without needing any intervention from you. If you see a prompt asking for a passphrase like the ones from the "Encrypt SteamOS and Recovery Partition" section, that may be a sign that something has been tampered with. If all or some of your files or settings are unexpectedly missing or changed, this can be a sign that something has been tampered with. Consider setting a unique custom boot video and/or adding a line like `echo my_secret_phrase` to the end of your .bashrc (replace my_secret_phrase with your own unique phrase) so that if your OS is not encrypted, your video won't play and your secret phrase won't be displayed making it more obvious that your firmware, ESP binary or encrypted partitions have been tampered with.

If you suspect that something's amiss, you can investigate:

  1. If SteamOS or your recovery partition show signs of tampering, try booting the other. If one still automatically decrypts and boots and does not show any signs of tampering, then you can be confident your firmware has not been altered and you can use the safe/untampered OS for the following steps. If you are not confident that at least one of your OS have not been tampered with, you will need a device separate from your Deck that you trust to be secure.

  If you have a safe/untampered OS you can still boot into:
  2. If your safe OS is your recovery partition, skip to "To restore SteamOS". If not, boot into your safe OS (SteamOS).
  3. Use your safe OS to check if you can still mount your partition(s) using your backed up keys and make sure files are how you'd expected them. Check your .bashrc file if you set it up.
  4. If your files are not as you expect, erase the partition and recreate it per the "Setup Recovery Partition" section.
  5. Remove any files on the SD card that do not belong to Windows or your recovery partition.
  6. Follow the recovery partition parts of the "Encrypt SteamOS and Recovery Partition" section
  7. You're now done. Both your OS should be secure. Ensure everything's in order with both. Consider running a virus scan on or even reinstalling Windows.

  If you think both of your OS may have been tampered with:
  2. Remove your SD card from the Deck, place it in a different trusted device and use that device to verify that your recovery partition can still be decrypted using your backed up key for it. Make sure your files are as you'd expect them. Check your boot video or .bashrc files if you set them up.
  3. Use the trusted device to compare the ESP binary on the SD card to your backup.
  4. If the partition is missing or altered, use your trusted device to erase it and recreate it per the "Setup Recovery Partition" section. Skip the step where you run `grub-install`! You will have to manually encrypt the partition with the backed up key and manually set the UUID of the recreated partition to match the original. Be sure to put a secret phrase in .bashrc even if you didn't originally.
  5. Restore the ESP binary from your backup if the one on your SD card is missing or altered.
  6. Remove any files on the SD card that do not belong to Windows or your recovery partition.
  7. Try booting into your recovery partition. It should automatically decrypt. Open xterm and make sure your secret phrase is displayed. If it is, skip to "To restore SteamOS". If you run into any issues, retrace your steps to make sure you didn't miss anything. If you're sure you've restored both your ESP binary and your recovery partition, and the TPM still refuses to release the key then either your firmware has been altered or the keys have been evicted from the TPM. Unfortunately, there is no way to verify your firmware is secure at this point. Your options are to replace the Deck's motherboard with a new one, to [reflash your firmware](https://www.reddit.com/r/SteamDeck/comments/123ml95/how_to_reflash_your_steam_deck_bios_chip) (assuming you made a backup of it already) or to hope that your firmware is still secure and that the keys were just evicted and to reinstall SteamOS, reseal your keys and keep using your Deck regardless.

  To restore SteamOS:
  8. Boot into your recovery partition and use your backed up key to mount your SteamOS home partition
  9. Check for your files for anything unexpected. Check .bashrc and your boot video if you set them up previously.
  10. Back up any irreplaceable files somewhere secure. Check files carefully for any tampering.
  11. You'll need another micro SD card (8 GB minimum) which you don't mind erasing. Find one or backup your current SD card's contents to a secure device then follow the [Steam Deck Recovery Instructions](https://help.steampowered.com/en/faqs/view/1B71-EDF2-EB6D-2BB3) to wipe your old SteamOS install and replace it with a fresh one. Restore the contents of your SD card if you used the same card for this step as the prior ones.
  12. Restore any of the irreplaceable files you previously backed up.
  13. Re-encrypt SteamOS per the "Encrypt SteamOS and Recovery Partition" section of the guide.
  14. Both of your OS should now be re-secured. Consider running a virus scan on or even reinstalling Windows.

Note that SteamOS uses a two-stage UEFI setup where the first stage (on the partition labeled "esp") chainloads a second bootloader on another partition. There are three pairs of partitions for the second stage, file system root and for /var (labeled efi-A, efi-B, rootfs-A, rootfs-B, var-A and var-B respectively). These are designed so that SteamOS has backup partitions it can use if the main ones are broken. There is also a large home partition where all user data is stored (e.g. games, game saves, apps, documents, downloads, settings, etc). auto_tpm_encrypt.py only encrypts the currently used root, var and home partitions and bypasses the SteamOS bootloaders with its own. SteamOS overwrites the partitions which are not in use during updates so the fact that these partitions are not encrypted shouldn't matter as they'll just be overwritten. You shouldn't need to boot into or use anything from the unencrypted partitions just be aware that, as they are unencrypted, they should not be considered safe until they are wiped.

Also note that AMD often puts out security updates for their firmware frequently including for the TPM in the Steam Deck. These updates are distributed via the normal SteamOS update process (From Game Mode: Settings > System > Check for Updates). Be sure to keep your Steam Deck up to date. See the "Updating SteamOS" section below for details.



## (Optional) Set SteamOS to Auto-Mount your Recovery Partition

There are two ways to use your recovery partition: you can keep it sandboxed and completely isolated from SteamOS or you can use your recovery partition for additional storage, just as you would with any other SD card in SteamOS. To isolate the two OS from each other, simply move your all your keys and other backups created by auto_tpm_encrypt.py somewhere secure that is not your SteamOS or recovery partitions then securely delete those files from those partitions. To use the recovery partition for storage, follow the steps below:

1. As root, create the file `/root/.local/bin/mount_encrypted_sd` with these contents, substituting your recovery partition for `mmcblk0p4` and the path you your recovery partition key for `/root/mykeyfile.bin`:
```
#!/bin/bash

cryptsetup open /dev/mmcblk0p4 sdlinux --perf-no_read_workqueue --keyfile /root/mykeyfile.bin
mount /dev/mapper/sdlinux /home/deck/sdlinux
```

2. Still as root, edit `/etc/sudoers` and add a line with `deck ALL=(root) NOPASSWD: /usr/bin/bash /root/.local/bin/mount_encrypted_sd` to the end

3. As the `deck` user, create the mountpoint with `mkdir /home/deck/sdlinux`

4. Still as the `deck` user, create `~/.config/systemd/user/encrypted_sd.service` with the following contents:
```
[Unit]
Description=Mount Encrypted SD

[Service]
Type=exec
ExecStart= /usr/bin/sudo /usr/bin/bash /root/.local/bin/mount_encrypted_sd

[Install]
WantedBy=default.target
```

5. Also as `deck`, Enable the service with the command `systemctl --user enable encrypted_sd`. This will automatically decrypt and mount your recovery partition at `/home/deck/sdlinux`. Reboot and ensure it works. Steam should automatically detect your partition and let you move or install games to it after a few minutes. Some other programs, such as Bottles, may need to be explicitly told where to find your recovery partition before they'll let you install anything to it.

6. Alternatively, if you don't always want the partition mounted, you can skip creating and enabling the encrypted_sd service and run `chmod +x /root/.local/bin/mount_encrypted_sd`. Then, you can manually mount it whenever you want it by running `sudo /root/.local/bin/mount_encrypted_sd`. If you do, adding the mount_encrypted_sd.sh script to sudoers is also optional; it just makes it so the script will run without prompting you for a password.


## Updating SteamOS

The vast majority of SteamOS updates will automatically install as normal while SteamOS is encrypted, however, a small number of updates which modify the kernel or firmware will fail to install. To install them follow the steps below. Do not boot Windows in the middle of the process.

1. From SteamOS, run `sudo python /root/.local/bin/auto_tpm_encrypt.py`, select "Add blank password to unbooted partition" and follow the prompts to make your recovery partition bootable without a key

2. From your recovery partition, run `sudo python /root/.local/bin/auto_tpm_encrypt.py`, select "Encrypt/Decrypt an unbooted partition" and follow the prompts to decrypt SteamOS

3. Back in SteamOS, install the update from Settings > System > Check For Updates

4. From your recovery partition, run `sudo python /root/.local/bin/auto_tpm_encrypt.py`, select "Encrypt/Decrypt an unbooted partition" and follow the prompts to encrypt SteamOS

5. Still from your recovery partition, run `sudo python /root/.local/bin/auto_tpm_encrypt.py`, select "Setup TPM auto-decrypt for the booted OS" and follow the prompts to reseal the key for your recovery partition

6. Verify both OS are encrypted


## FAQ

#### Q: What is UEFI? What's an ESP? What's an ESP binary?

A: [Unified Extensible Firmware Interface](https://en.wikipedia.org/wiki/UEFI) (UEFI) is an interface designed to standardize how operating systems and hardware talk to each other. Devices that use UEFI store the code that's used to boot operating systems in an [EFI system partition](https://en.wikipedia.org/wiki/EFI_System_partition) (ESP) on their storage device. An ESP is just a [FAT](https://en.wikipedia.org/wiki/FAT_file_system) partition with the partition type marked as ESP in the [partition table](https://en.wikipedia.org/wiki/GUID_Partition_Table). ESP contain [binaries](https://en.wikipedia.org/wiki/Executable) which are used to load and boot into operating systems. Many ESP binaries just act as [second-stage bootloaders](https://en.wikipedia.org/wiki/Bootloader#Second-stage_boot_loader), doing just enough to find and load the OS' kernel but, ESP binaries can contain an operating system's bootloader, [kernel](https://en.wikipedia.org/wiki/Kernel_(operating_system)), [initial file system](https://en.wikipedia.org/wiki/Initial_ramdisk), configuration files and programs all within a single fie.


#### Q: What exactly is a TPM? How does it work? What's sealing?

A: A [Trusted Platform Module](https://en.wikipedia.org/wiki/Trusted_Platform_Module) or TPM is a component within a device which is designed to ensure that code running on the device can be trusted. TPMs are often designed to be tamper-proof and support many different security related functions. TPMs contain [Platform Configuration Registers](https://security.stackexchange.com/questions/252391/understanding-tpm-pcrs-pcr-banks-indexes-and-their-relations) (PCRs) which store the [hashes](https://en.wikipedia.org/wiki/Hash_function) of various pieces of software running on the device. For example, PCR0 is the hash of the device's firmware and PCR2 is the hash of the booted ESP binary. A full list of PCRs can be found [here](https://wiki.archlinux.org/title/Trusted_Platform_Module#Accessing_PCR_registers). To prevent malicious code from impersonating trusted code, PCRs can be extended but can not be reset without powering off the device. TPMs contain a hardware component known as a static root of trust which runs code which can not be modified which extends the PCR used for the device's firmware. As a result, even if the firmware is replaced with a modified version, the TPM will know. Sealing is a process where a small amount of data can be stored securely within the TPM. When sealing data, the TPM is given a list of PCRs. The TPM stores the hashes of the given PCRs along with the data. To later retrieve the data, it must be unsealed. The TPM will only unseal the data if the PCRs at the time of unsealing match the PCRs at the time of sealing.

auto_tpm_encrypt.py generates a random key and encrypts partitions with that key. The script creates an ESP binary which combines the bootloader, kernel, kernel args, initial file system and all of the programs and configuration files needed to unseal the encryption key from the TPM and decrypt and boot the rest of the OS all in one file. Because all of that is stored in the ESP binary, a change to any of those elements will change PCR2. The script later seals the random key using PCR0 (the firmware) and PCR2. As a result, the TPM will only release the encryption key if the firmware, kernel, etc all have been left unaltered. When using the TPM to store encryption keys this way, the TPM ensures that each OS can only access its own keys. Without the encryption keys, other operating systems can't read or modify the data. This protects against attacks like the [evil maid attack](https://en.wikipedia.org/wiki/Evil_maid_attack).


#### Q: How do I uninstall everything auto_tpm_encrypt.py installed?

A: Everything the script does should be reversible. Run `sudo python auto_tpm_encrypt.py`, select "Encrypt/Decrypt an unbooted partition" and follow the prompts to decrypt each of your OS. When encrypting, the script will output a list of files it created as backups. Delete all of these backup files. The script should also show any packages it installs as it runs. If you no longer want these packages, you may uninstall them. You may also re-enable read-only mode for SteamOS via `steamos-readonly enable`. With everything decrypted, SteamOS should be identical to how it was stock.


#### Q: Why uncheck "Remove requirement for an online Microsoft account" when using Rufus to install Windows?

A: Not having support for [MSA](https://en.wikipedia.org/wiki/Microsoft_account) enabled may delay or prevent Windows updates from installing. It's particularly important in the context of gaming to have the latest security updates, certificates, etc installed as [malware has been known to use kernel anti-cheat drivers to gain low level access](https://www.trendmicro.com/en_vn/research/22/h/ransomware-actor-abuses-genshin-impact-anti-cheat-driver-to-kill-antivirus.html) to Windows systems.


#### Q: Why does auto_tpm_encrypt.py refuse to run unless the Steam Deck is plugged in to a charger?

A: The script is designed to abort as soon as possible if it detects anything amiss to avoid corrupting or breaking anything. It's also designed so that, if it does abort, it will leave behind enough data that you can investigate why it failed and either manually finish what it started or undo whatever it did. For example, it writes a backup of the encryption key it generated to disk before it starts encrypting anything. Even so, there are still spots in the script (such as in the middle of encrypting a partition) where having your Steam Deck's battery die could cause your data to be corrupted. The script has several points where it will abort if your Deck is not plugged in. These are designed to stop the script at a safe place where there is no risk of data being corrupted rather than risk continuing and possibly having the battery die.


#### Q: What does "WARNING! The contents of your ESP do not match what was recorded in the manifest." mean?

A: auto_tpm_encrypt.py creates files called the ESP manifests which contains the names and hashes of all files stored on your [ESPs](https://en.wikipedia.org/wiki/EFI_system_partition). The ESP binaries auto_tpm_encrypt.py builds (e.g. Auto_TPM_Encrypted_Boot.efi) does not depend on any external files and it is used to seal your encryption key in the TPM. As such, while your OS is encrypted, you'll immediately know if someone or something has tampered with your ESP as the TPM will not unseal the key, your files will fail to decrypt without the key and you'll see an error when trying to boot. Once you have decrypted, you no longer have that protection so it is important to make sure that any changes made to your ESP are not malicious. The ESP manifests are stored in the paths specified by ESP_MANIFEST_PATH and STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX in auto_tpm_encrypt.py. By default, these paths are `/root/.local/state/auto_tpm_encrypt/auto_tpm_encrypt_esp_manifest.json` and, for SteamOS, `/root/.local/state/auto_tpm_encrypt/auto_tpm_encrypt_steamos_second_stage_esp_manifest.efi-A.json` and `/root/.local/state/auto_tpm_encrypt_steamos_second_stage_esp_manifest.efi-B.json`. The manifests are JSON files containing a object who's keys are the timestamp of each update to the manifest and who's values are objects which use file and folder paths for their keys and the SHA256 hash of each file for their values. Compare each ESP manifest to your ESP and undo any changes you don't recognize or wipe the ESP and recreate it from scratch, whichever you find easiest. During encryption, both the firmware and ESP binary are used to seal the key so it is safe to assume that your firmware has not been tampered with if you have not had any issues with booting your encrypted OS's up until now.


#### Q: How do I fix the error `error: package-name: signature from "packager" is unknown trust` or `error: package-name: signature from "packager" is marginal trust`?

A: See [this page](https://wiki.archlinux.org/title/Pacman/Package_signing#Signature_is_unknown_trust) on the Arch Wiki. If you get the error `Partition / is mounted read only` while updating keys, you can run `mount -o rw,remount /` as root.


#### Q: How do I fix the error `<ci-package-builder-1@steamos.cloud> is unknown trust`?

A: Follow the steps from the above answer. If they don't work, try `sudo pacman-key --refresh-keys` and run the command that gave that error again. If you are still getting that error, run `sudo pacman-key --lsign-key 889B5EBDDD505A683621900DAF1D2199EF0A3CCF` to manually mark the key for Valve's [CI bot](https://en.wikipedia.org/wiki/Continuous_integration) as trusted. On prior SteamOS images, this was already done automatically. At the time that I'm writing this, on the latest update, the key is not marked as trusted. Hopefully, this will be fixed soon.


#### Q: What do "No free persistent TPM handles!" or "No free slots to store sealed key." mean?

A: TPMs are able to store a small amount of data which will persist even after the device they're in is turned off. Each piece of data stored in the TPM has a handle which is a unique identifier which can be used when dealing with that data. TPMs have a limited number of persistent pieces of data they can store. For the Steam Deck's TPM, this limit is five pieces of data. Each OS encrypted by auto_tpm_encrypt.py will use one of the five "slots" so encrypting both SteamOS and the recovery partition uses two of the five slots. Other OS can use more. Windows doesn't seem to be consistent in how many handles it takes up but I've seen it use as many as four of the Steam Deck's five slots. If your TPM runs out of handles, you can make room by evicting handles you are no longer using. You'll first need to figure out which handles you are still using. auto_tpm_encrypt.py uses the function get_existing_tpm_address_from_hooks() to check which handles are still in use so you can use that function as a reference. In most cases, you can just check `/etc/auto_tpm_unseal` for the handle. It will be an hex address like `0x80000000`. Check each of your encrypted OS an take note of all in use handles. Then, run `tpm2_getcap handles-persistent` to list all handles that are in your TPM. For any handles not already in use, you can run `tpm2_evictcontrol --hierarchy o --object-context 0x80000000` to evict them, substituting the handle's address for 0x80000000. In my experience, you can safely evict any handles Windows tries to claim without causing any issues; just be prepared to potentially need to reenter your password or pin the next time you log in to Windows.


#### Q: What's the deal with the settings which "aren't designed to be changed" at the top of auto_tpm_encrypt.py?

A: These settings basically fall into three categories: settings which were experimental but are now tested and stable enough to leave on by default, old settings which are no longer maintained but which should still work and options which can be used to tweak the script's behavior. Currently, auto_tpm_encrypt.py is specific to the Steam Deck and the quirks of SteamOS but it is designed to be generic enough that it could be used for other Linux distros and devices. The script has been tested mainly with the default settings so you'll get the best results if you leave them alone but, if you want to get the script running on something that's not the Steam Deck or if you want to tweak the script's behavior, you might try changing some of the settings. A brief description of each setting is below:

 - USE_SYSTEMD_INIT: When true, uses [systemd](https://en.wikipedia.org/wiki/Systemd) for services, the initramfs, etc. When false, [udev](https://en.wikipedia.org/wiki/Udev) is used.
 - BLANK_PASSWORD: When partitions are initially encrypted, they are temporarily encrypted with an empty string as a valid password so that the OS can be booted and the key can be sealed. This blank password is removed from the encrypted partitions by the "Setup TPM auto-decrypt for the booted OS" function of the script. An empty string is used because it is the only password that can be typed on a Steam Deck at boot without having to connect an external keyboard. BLANK_PASSWORD controls what password is used for this tempory password. If you have an external keyboard and you want to use a more secure tempory password, you can set what password is used here.
 - FILESYTEM_WAIT_ITERATION_TIME: Time in seconds that the script will wait before polling the file system to see if it is ready. Shorter times means more frequent polling.
 - FILESYTEM_WAIT_TOTAL_TIME: Time in seconds that the script will wait before timing out when waiting for a file system to be ready. Increasing this may help if the script times out though the default is already very long (3 minutes).
 - KEY_LENGTH_IN_BYTES: As the name implies, controls how many bytes long the randomly generated encryption keys are. The default value is set to the maximum, most secure length that can fit within the Steam Deck's TPM. Increasing the length to further increase security may be possible on non-Steam Deck hardware depending on your TPM.
 - DO_MASK_STEAMCL_SERVICE: When true, disable the steamos-install-steamcl service until SteamOS is decrypted. The steamcl service is used to check Stem OS' chainloader and restore it if it is not enabled. auto_tpm_encrypt.py bypasses the SteamOS chainloader and installs its own ESP binary which supports encryption. Disabling the steamcl service prevents SteamOS from replacing the new ESP binary with the old one which would prevent SteamOS from booting.
 - RD_LUKS_TIMEOUT: Disabled by default. Specifies the number of seconds to wait before timing out at a passphrase prompt.
 - RD_LUKS_TRY_EMPTY_PASSWORD: Disabled by default. Leave this disabled! When set to true, the passphrase prompt will be skipped if an empty password is present on the partitions. This saves you from having to press the A button during setup, however, this can lead you to not realize that you haven't finished sealing your key if you forget to run the "Setup TPM auto-decrypt for the booted OS" option. Having the passphrase screen be displayed is a security feature designed to act as a reminder to finish setting up encryption.
 - RD_LUKS_NO_READ_WORKQUEUE: Enabled by default. Improves performance by performing read ops directly without going through the workqueue.
 - DISABLE_GPT_AUTO: Set to true by default. When true, disables the [systemd-gpt-auto-generator](https://www.freedesktop.org/software/systemd/man/latest/systemd-gpt-auto-generator.html) during early boot. This prevents the generator from trying to mount the encrypted partitions, which it will fail to do as it does not support encrypted partitions.
 - SHOW_KERNEL_MESSAGES_AT_BOOT: Enabled by default. When true, kernel message showing your systems status will be displayed during boot. When false, your Steam Deck will just show a black screen instead.
 - ENABLE_IOMMU: Enabled by default. When true, enables [IOMMU](https://en.wikipedia.org/wiki/Input%E2%80%93output_memory_management_unit) support for the kernel. This option has no effect on the behavior or performance of anything but it is left enabled as having IOMMU support may be useful in some circumstances. It is a relic of an early iteration of this project which attempted to boot Windows within SteamOS using [KVM](https://linux-kvm.org/page/Main_Page) and [VFIO](https://docs.kernel.org/driver-api/vfio.html) to pass the Deck's GPU through to the VM. Unfortunately, the Deck's GPU driver did not support switching power states, as required to detach it from SteamOS and attach it to Windows, and the [Deck's IOMMU groups](https://www.reddit.com/r/SteamDeck/comments/taygzo/technical_documentation) do not fully isolate the GPU from other hardware on the Deck, such as its controller. As such, the project ended up shifting focus to using the TPM for secure dual booting rather than using VFIO to pass through the GPU to a VM.
 - USE_ESP_MANIFEST: Enabled by default. When true, creates and verifies ESP manifests. See the question above about the "WARNING! The contents of your ESP do not match what was recorded in the manifest." message for details.
 - ESP_MANIFEST_PATH: Sets the path used to store the ESP manifest. If you change this, make sure it is not a path that will be used by another file.
 - USE_STEAMOS_SECOND_STAGE_ESP_MANIFEST: Enabled by default. When true, ESP manifests are created for SteamOS' second stage ESP.
 - STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX: Sets the path and prefix used to generate filenames for second stage ESP manifests. Make sure this prefix won't conflict with a path used by any other programs.
 - STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_EXTENSION: Sets the extension used for second stage ESP manifests

#### Q: Why disable read workqueues but not write workqueues?

A: Disabling read and write workqueues for encrypted drives improves performance, which is why RD_LUKS_NO_READ_WORKQUEUE is enabled by default. However, some older kernels had issues where disabling write workqueues would lead to synchronization issues which caused data to be corrupted. I haven't been able to find a comprehensive list of all bugs related to these issues so I also have not been able to verify that the kernel which ships with SteamOS does not have this issue. Once I'm confident it doesn't, I'll likely add a RD_LUKS_NO_WRITE_WORKQUEUE which is enabled by default.


#### Q: Why is TRIM disabled? Why not enable TRIM?

A: For encrypted file systems, [TRIM can reveal information about the underlying file system](https://asalor.blogspot.com/2011/08/trim-dm-crypt-problems.html) which weakens the security of the encryption.


#### Q: What is LizardShell.py?

A: LizardShell is a small text based terminal emulator combined with an on-screen keyboard designed to be run while the Steam Deck's controls are in ["Lizard Mode"](https://www.reddit.com/r/SteamController/comments/41329r/eli5_what_is_lizard_mode). When it starts, the Steam client disables Lizard Mode and maps the Deck's controls to the desktop controller layout, the layout for whatever game you're playing, etc. Lizard Mode is the default mode that the Deck's controls start in and it's designed as a fallback in case Steam doesn't load correctly. Lizard Mode maps the D-Pad to the arrow keys, the A button to Enter, the right touch pad to the mouse, etc. LizardShell is designed to enable controlling a terminal using the Deck's D-Pad and A button while the Deck is still in Lizard Mode. LizardShell runs from a basic VGACON console and its original purpose was to avoid the need to install a window manager, on screen keyboard program and all of their dependencies to the recovery partition in order to save space and keep the recovery partition small. LizardShell is about 80% complete. It works but there are more bugs in it than were worth fixing. I've included LizardShell as a curiosity since some people may find it interesting. I eventually abandoned it in favor of just using Fluxbox and CoreKeyboard. Both are small but there is still some room for improvement regarding shrinking the space needed for the recovery partition.


#### Q: Can this be used on a device that's not a Steam Deck?

A: AutoTpmEncrypt supports any Arch Linux based operating system. winsetup.bat and its accompanying files are also designed to be generic and work on any Windows install, for both real hardware and VMs; they've been tested on several Windows devices in addition to the Steam Deck.
