# A small tool designed to detect if the firmware for the deck's controls
# has been tampered with. Will exit with a return code of 0 if the firmware
# passes and a non-zero value if any issues are found. Non-comprehensive but
# should offer some protection against the firmware being altered.

device_info_path = '~/.config/.steamdeck_controller_audit.json'
fw_path = '/usr/share/jupiter_controller_fw_updater'
debug_fw_dump_path = '~/.config/steamdeck_controller_firmware_dump.dbg'
debug_dump_controller_firmware = False

import sys, os, re, platform, json
sys.path.append(fw_path)

is_steamos = re.match(r'[\d\.\-]+valve[\d\.\-]+neptune[\d\.\-]*$', platform.release()) is not None
if not is_steamos:
  print('Not SteamOS, skipping firmware audit')
  sys.exit()
else:
  print('Checking controller firmware...')

import d20bootloader
with d20bootloader.DogBootloader(mcu=d20bootloader.DogBootloaderMCU.PRIMARY,
                                 reset=False) as bootloader:
  device_type = bootloader.device_type

all_firmwares = [open(i,'rb').read() for i in map(lambda i: os.path.join(fw_path, i),
                                             filter(lambda i: i.endswith('.bin'),
                                                    os.listdir(fw_path)))]

try:
  with open(os.path.expanduser(device_info_path), 'r') as f:
    old_device_info = json.load(f)
except FileNotFoundError:
  old_device_info = None

def fw_blob_matches_app_fw(fw_blob, app_fw):
  if not app_fw.startswith(fw_blob):
    return False
  delta = len(app_fw) - len(fw_blob)
  if delta > 0:
    if app_fw[-delta:].count(b'\xFF') != delta:
      return False
  return True

def verify_firmware(bootloader, size):
  downloaded_firmware = bootloader.download_firmware(size)
  if debug_dump_controller_firmware:
    with open(os.path.expanduser(debug_fw_dump_path), 'wb') as f:
      f.write(downloaded_firmware)
  assert(any((fw_blob_matches_app_fw(firmware, downloaded_firmware)
         for firmware in all_firmwares)))

device_info = {}
if device_type == d20bootloader.DeviceType.D21_D21:
  import d21bootloader16
  with d21bootloader16.DogBootloader() as bootloader:
    serials = bootloader.board_serial
    hardware_ids = bootloader.hardware_id
    unique_ids = bootloader.unique_id
    for i, prefix in enumerate(('primary', 'secondary')):
      device_info[prefix+'_board_serial'] = serials[i]
      device_info[prefix+'_hardware_id'] = hardware_ids[i]
      device_info[prefix+'_unique_id'] = unique_ids[i]
      device_info[prefix+'_user_row'] = bootloader.user_row[i].hex()
    verify_firmware(bootloader, d21bootloader16.APP_FW_LENGTH)
    for code in (d21bootloader16.DEBUG_READ_32B_THIS,
                 d21bootloader16.DEBUG_READ_32B_OTHER):
      failed = False
      try:
        val = bootloader._read_debug_data(code, size=4, offset=0)
      except:
        failed = True
      assert failed, f'Read that should have failed suceeded {code}:{val}'
    try:
      bootloader.reboot()
    except d21bootloader16.hid.HIDException:
      pass
else:
  for primary in (True, False):
    if not primary and device_type != d20bootloader.DeviceType.D2x_D21:
      continue
    with d20bootloader.dog(primary) as bootloader:
      prefix = 'primary' if primary else 'secondary'
      device_info[prefix+'_board_serial'] = bootloader.board_serial
      device_info[prefix+'_hardware_id'] = bootloader.hardware_id
      device_info[prefix+'_unique_id'] = bootloader.unique_id
      if bootloader.device_type == d20bootloader.DeviceType.D2x_D21:
        device_info[prefix+'_user_row'] = bootloader.user_row.hex()
      verify_firmware(bootloader, bootloader.APP_FW_LENGTH)
      failed = False
      try:
        val = bootloader.read_32b(0x0)
      except d20bootloader.hid.HIDException:
        failed = True
      assert failed, f'Read that should have failed suceeded {val}'
    try:
      bootloader.reboot()
    except d20bootloader.hid.HIDException:
      pass

print(device_info)
if old_device_info is None:
  with open(os.path.expanduser(device_info_path), 'x') as f:
    json.dump(device_info, f)
else:
  assert device_info == old_device_info

print('Audit Passed!')
