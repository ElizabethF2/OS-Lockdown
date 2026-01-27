#!/usr/bin/env python3

import sys, os, re, shutil, subprocess, tempfile

HELP_TEXT = '''
Usage: nvdata_tool [option]...
  --enable-usb-boot or -e
  --disable-usb-boot or -d
  --enable-boot-on-ac-detect
  --disable-boot-on-ac-detect
  --work-dir DIR                 Store firmware to DIR
  --dump                         Dump firmware and nvdata without modification
  --status or -s                 View flag status
  --rm or -r                     Remove the work dir if there are no errors
  --help or -h                   Show this help message
'''.lstrip()

# https://chromium.googlesource.com/chromiumos/platform/vboot_reference/+/master/firmware/2lib/include/2nvstorage_fields.h
# see also:
#   https://chromium.googlesource.com/chromiumos/platform/vboot_reference/+/master/firmware/2lib/include/2nvstorage.h
VB2_NV_OFFS_HEADER = 0x00
VB2_NV_OFFS_DEV = 0x04
VB2_NV_OFFS_MISC = 0x08
VB2_NV_OFFS_CRC_V1 = 0x0F
VB2_NV_OFFS_CRC_V2 = 0x3F
VB2_NV_OFFS_RESERVED_V2 = 0x0F
VB2_NV_DEV_FLAG_EXTERNAL = 0x01
VB2_NV_MISC_BOOT_ON_AC_DETECT = 0x02
VB2_NV_HEADER_SIGNATURE_V1 = 0x40
VB2_NV_HEADER_SIGNATURE_V2 = 0x03

# https://chromium.googlesource.com/chromiumos/platform/vboot_reference/+/master/firmware/2lib/2crc8.c
def crc8(buf):
  crc = 0
  for b in buf:
    crc ^= (b << 8)
    for _ in range(8):
      if crc & 0x8000:
        crc ^= 0x8380
      crc <<= 1
  return crc >> 8

def main():
  args = sys.argv[1:]
  if not args or '--help' in args or '-h' in args:
    print(HELP_TEXT)
    return

  if not (flashrom := shutil.which('flashrom')):
    raise Exception('flashrom is missing - please install it')

  with open('/sys/firmware/log', 'r') as f:
    firmware_log = f.read()

  if '\nvb2' not in firmware_log.lower():
    raise Exception('Unsupported firmware revision')

  # nvdata = re.findall('nvdata:([ A-Fa-f0-9]+)', firmware_log)
  # if len(nvdata) < 1:
  #   raise Exception('Unable to find nvdata in firmware log. Reboot your device then, after it has rebooted, power it off by holding the power button then power it back on.')
  # if len(nvdata) != 1:
  #   raise Exception('Unexpected nvdata count')
  # nvdata = bytes.fromhex(nvdata[0].replace(' ', ''))
  # if len(nvdata) != 16:
  #   raise Exception('Unexpected nvdata length')

  pair = list(set(re.findall(
    r'FMAP: area RW_NVRAM found @ ([a-fA-F0-9]+) \((\d+) bytes\)',
    firmware_log,
  )))
  if len(pair) != 1:
    raise Exception('Unexpected RW_NVRAM count')
  offset = int(pair[0][0], 16)
  bufsize = int(pair[0][1])

  created_paths = []
  try:
    wdir = args[args.index('--work-dir')+1]
  except (ValueError, IndexError):
    wdir = tempfile.mkdtemp(prefix = 'nvdata_')
    created_paths.append((True, wdir))
  print('@@@ Work Dir:', wdir)

  print('@@@ Reading current nvdata from flash')
  original_fpath = os.path.join(wdir, 'original.bin')
  subprocess.check_call((flashrom, '-p', 'linux_mtd', '-r', original_fpath))
  created_paths.append((False, original_fpath))
  with open(original_fpath, 'rb') as f:
    original_fw = f.read()

  if original_fw[offset + VB2_NV_OFFS_HEADER] & VB2_NV_HEADER_SIGNATURE_V1:
    vbnv_size = 16
  elif original_fw[offset + VB2_NV_OFFS_HEADER] & VB2_NV_HEADER_SIGNATURE_V2:
    vbnv_size = 64
  else:
    raise Exception('Invalid or unknown VB2 header')

  if bufsize % vbnv_size != 0:
    raise Exception('Area size and vbnv size do not match')

  end = offset + bufsize
  updated_fw = list(original_fw)
  last = None
  while offset < end:
    nvdata = original_fw[offset:offset+vbnv_size]
    if nvdata == (b'\xFF' * vbnv_size):
      break
    print('@@@ Found NVDATA:', nvdata.hex(), 'at offset', hex(offset))
    last = offset
    offset += vbnv_size

  if '--dump' in args:
    print('@@@ Firmware dumped to:', original_fpath)
    return

  if last is None:
    raise Exception('Unable to find NVDATA')

  if '--status' in args or '-s' in args:
    usb_boot = original_fw[last + VB2_NV_OFFS_DEV] & VB2_NV_DEV_FLAG_EXTERNAL
    print('@@@ USB Boot:         ', usb_boot)
    boot_on_ac_detect = original_fw[last + VB2_NV_OFFS_MISC] & VB2_NV_MISC_BOOT_ON_AC_DETECT
    print('@@@ Boot on AC Detect:', boot_on_ac_detect)
  else:
    if '--enable-usb-boot' in args or '-e' in args:
      updated_fw[last + VB2_NV_OFFS_DEV] |= VB2_NV_DEV_FLAG_EXTERNAL
    elif '--disable-usb-boot' in args or '-d' in args:
      updated_fw[last + VB2_NV_OFFS_DEV] &= ~VB2_NV_DEV_FLAG_EXTERNAL
    if '--enable-boot-on-ac-detect' in args:
      updated_fw[last + VB2_NV_OFFS_MISC] |= VB2_NV_MISC_BOOT_ON_AC_DETECT
    elif '--disable-boot-on-ac-detect' in args:
      updated_fw[last + VB2_NV_OFFS_MISC] &= ~VB2_NV_MISC_BOOT_ON_AC_DETECT
    if vbnv_size == 16:
      updated_fw[last + VB2_NV_OFFS_CRC_V1] = crc8(updated_fw[last:last+VB2_NV_OFFS_CRC_V1])
    else:
      updated_fw[last + VB2_NV_OFFS_RESERVED_V2] = 0xFF
      updated_fw[last + VB2_NV_OFFS_CRC_V2] = crc8(updated_fw[last:last+VB2_NV_OFFS_CRC_V2])
    print('@@@ New NVDATA:', bytes(updated_fw[last:last+vbnv_size]).hex())

    updated_fw = bytes(updated_fw)
    if updated_fw == original_fw:
      raise Exception('New nvdata matches current nvdata - nothing to do')

    updated_fpath = os.path.join(wdir, 'updated.bin')
    with open(updated_fpath, 'xb') as f:
      f.write(updated_fw)
    created_paths.append((False, updated_fpath))

    print('@@@ Writing updated nvdata to flash')
    subprocess.check_call((flashrom, '-p', 'linux_mtd', '--flash-contents', original_fpath, '-w', updated_fpath))

  print('@@@ Done!')

  if '--rm' in args or '-r' in args:
    for is_dir, path in reversed(created_paths):
      os.rmdir(path) if is_dir else os.remove(path)

if __name__ == '__main__':
  main()
