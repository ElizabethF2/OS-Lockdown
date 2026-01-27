#!/usr/bin/env python3



import sys, os, subprocess, platform, re, shutil, json, functools, tempfile
import stat, math, time, shlex, hashlib

try:
  import readline
except ModuleNotFoundError:
  pass

ESP_GUID = 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b'
BASIC_DATA_GUID = 'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7'
TPM_RH_OWNER = 'o'

SUCCESS = 0
ALREADY_UNMOUNTED = 1
HANDLE_NOT_FOUND = 1
PASSPHRASE_NOT_FOUND = 2
DEVICE_IN_USE = 5

SUPPORTED_UNENCRYPTED_FILESYSTEMS = ('ext2', 'ext3', 'ext4', 'btrfs')
SUPPORTED_ENCRYPTED_FILESYSTEMS = ('crypto_LUKS',)
SUPPORTED_FILESYSTEMS = (SUPPORTED_UNENCRYPTED_FILESYSTEMS +
                         SUPPORTED_ENCRYPTED_FILESYSTEMS)

WAKELOCK_SERVICES = ('sleep.target', 'suspend.target',
                     'hibernate.target', 'hybrid-sleep.target')

REMOVED_COMMENT = '# REMOVED_BY_AUTO_TPM_ENCRYPT '
ADDDED_COMMENT = ' # ADDED_BY_AUTO_TPM_ENCRYPT'

# These settings aren't designed to be changed and changing them may break stuff.
# Don't change any of these without reading the warnings in the guide first.
USE_SYSTEMD_INIT = bool(os.environ.get('AUTOTPM_USE_SYSTEMD_INIT', True))
BLANK_PASSWORD = os.environb.get(b'AUTOTPM_BLANK_PASSWORD', b'')
FILESYTEM_WAIT_ITERATION_TIME = float(os.environ.get('AUTOTPM_FILESYTEM_WAIT_ITERATION_TIME', 5))
FILESYTEM_WAIT_TOTAL_TIME = float(os.environ.get('AUTOTPM_FILESYTEM_WAIT_TOTAL_TIME', 180))
KEY_LENGTH_IN_BYTES = int(os.environ.get('AUTOTPM_KEY_LENGTH_IN_BYTES', 32))
DO_MASK_STEAMCL_SERVICE = bool(os.environ.get('AUTOTPM_DO_MASK_STEAMCL_SERVICE', True))
RD_LUKS_TIMEOUT = [i if i is None else int(i) for i in [os.environ.get('AUTOTPM_RD_LUKS_TIMEOUT')]][0]
RD_LUKS_TRY_EMPTY_PASSWORD = bool(os.environ.get('AUTOTPM_RD_LUKS_TRY_EMPTY_PASSWORD', False))
RD_LUKS_NO_READ_WORKQUEUE = bool(os.environ.get('AUTOTPM_RD_LUKS_NO_READ_WORKQUEUE', True))
DISABLE_GPT_AUTO = bool(os.environ.get('AUTOTPM_DISABLE_GPT_AUTO', True))
SHOW_KERNEL_MESSAGES_AT_BOOT = bool(os.environ.get('AUTOTPM_SHOW_KERNEL_MESSAGES_AT_BOOT', True))
ENABLE_IOMMU = bool(os.environ.get('AUTOTPM_ENABLE_IOMMU', True))
USE_ESP_MANIFEST = bool(os.environ.get('AUTOTPM_USE_ESP_MANIFEST', True))
ESP_MANIFEST_PATH = os.environ.get('AUTOTPM_ESP_MANIFEST_PATH', 'auto_tpm_encrypt_esp_manifest.json')
USE_STEAMOS_SECOND_STAGE_ESP_MANIFEST = bool(os.environ.get('AUTOTPM_USE_STEAMOS_SECOND_STAGE_ESP_MANIFEST', True))
STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX = os.environ.get('AUTOTPM_STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX',
                                                               'auto_tpm_encrypt_steamos_second_stage_esp_manifest.')
STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_EXTENSION = os.environ.get('AUTOTPM_STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_EXTENSION', '.json')
SKIP_CONTROLLER_FIRMWARE_AUDIT = bool(os.environ.get('AUTOTPM_SKIP_CONTROLLER_FIRMWARE_AUDIT', False))
USE_SECURE_BOOT_SIGNING = bool(os.environ.get('AUTOTPM_USE_SECURE_BOOT_SIGNING', True))
EFI_STUB_PATH = os.environ.get('AUTOTPM_EFI_STUB_PATH', '/usr/lib/systemd/boot/efi/linuxx64.efi.stub')
REBOOT_TIMER_DURATION = int(os.environ.get('AUTOTPM_REBOOT_TIMER_DURATION', 20))
PCR_LIST = os.environ.get('AUTOTPM_PCR_LIST', '0,2,4')
SHOULD_KILL_WINDOWS_BOOT_MANAGER = bool(os.environ.get('AUTOTPM_KILL_WINDOWS_BOOT_MANAGER', True))

STEAMCL_SERVICE_MASK_PATH = '/etc/systemd/system/steamos-install-steamcl.service'

INSTALL_HOOK_PATH = '/usr/lib/initcpio/install/auto_tpm_encrypt'
INSTALL_HOOK_TEMPLATE = """
#!/bin/bash
build() {
  add_module "tpm_crb"
  add_binary "/usr/lib/libtss2-tcti-device.so"
  add_binary "tpm2_unseal"
  add_runscript
}

help() {
    cat <<HELPEOF
Automatically unseals a previously stored encryption key from the TPM
non-systemd version
HELPEOF
}
""".lstrip()

SD_INSTALL_HOOK_TEMPLATE = r"""
#!/bin/bash
build() {
  add_module "tpm_crb"
  add_binary "/usr/lib/libtss2-tcti-device.so"
  add_binary "tpm2_unseal"

  add_file "$UNSEAL_SCRIPT_PATH"

  add_systemd_unit "auto_tpm_unseal.service"
  add_systemd_unit "cryptsetup-pre.target"

  WANTSDIR="/usr/lib/systemd/system/cryptsetup.target.wants"
  mkdir --parents "$BUILDROOT$WANTSDIR"
  add_symlink "$WANTSDIR/cryptsetup-pre.target" "/usr/lib/systemd/system/cryptsetup-pre.target"

  WANTSDIR="/usr/lib/systemd/system/cryptsetup-pre.target.wants"
  mkdir --parents "$BUILDROOT$WANTSDIR"
  add_symlink "$WANTSDIR/auto_tpm_unseal.service" "$UNSEAL_SERVICE_PATH"

  WANTSDIR="/usr/lib/systemd/system/system/etc.mount.wants"
  mkdir --parents "$BUILDROOT$WANTSDIR"
  add_symlink "$WANTSDIR/cryptsetup.target" "/usr/lib/systemd/system/cryptsetup.target"

  mkdir --parents "$BUILDROOT/etc/cryptsetup-keys.d"

  # Remove unused drivers to avoid running out of space
  lspci | grep -i polaris || \
    rm $BUILDROOT/usr/lib/firmware/amdgpu/polaris*
  lspci | grep -i topaz || \
    rm $BUILDROOT/usr/lib/firmware/amdgpu/topaz*
  lspci | grep -i tahiti || \
    rm $BUILDROOT/usr/lib/firmware/amdgpu/tahiti*
  lspci | grep -i fiji || \
    rm $BUILDROOT/usr/lib/firmware/amdgpu/fiji*
  lspci | grep -i vega || \
    rm $BUILDROOT/usr/lib/firmware/amdgpu/vega*
}

help() {
    cat <<HELPEOF
Automatically unseals a previously stored encryption key from the TPM
systemd version
HELPEOF
}
""".lstrip()

RUN_HOOK_PATH = '/usr/lib/initcpio/hooks/auto_tpm_encrypt'
RUN_HOOK_TEMPLATE = """
#!/usr/bin/bash
run_hook() {
    modprobe -a -q tpm_crb >/dev/null 2>&1
    tpm2_unseal -c $tpm_address -p pcr:$hash_algorithm:$pcr_list -o /crypto_keyfile.bin
}
""".lstrip()

UNSEAL_SCRIPT_PATH = '/etc/auto_tpm_unseal'
UNSEAL_SCRIPT_TEMPLATE = """
#!/usr/bin/bash
modprobe -a -q tpm_crb >/dev/null 2>&1
tpm2_unseal -c $tpm_address -p pcr:$hash_algorithm:$pcr_list -o /etc/cryptsetup-keys.d/tpm_encrypted_var.key
$reboot_timer_code
cp /etc/cryptsetup-keys.d/tpm_encrypted_var.key /etc/cryptsetup-keys.d/tpm_encrypted_root.key
cp /etc/cryptsetup-keys.d/tpm_encrypted_var.key /etc/cryptsetup-keys.d/tpm_encrypted_home.key
""".strip()

REBOOT_TIMER_SCRIPT_TEMPLATE = """
if [ "$?" != "0" ]; then
  (sleep $reboot_timer_duration ; kill -INT 1)&
  reboot_timer_pid=$!
  read -p "[Press enter to prevent a reboot]" 2> /dev/console < /dev/console
  kill -HUP $reboot_timer_pid > /dev/null
fi
""".strip()

UNSEAL_SERVICE_PATH = '/usr/lib/systemd/system/auto_tpm_unseal.service'
UNSEAL_SERVICE_TEMPLATE = """
[Unit]
Description=TPM Encryption Key Unsealing Service
DefaultDependencies=no
Before=cryptsetup-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh $UNSEAL_SCRIPT_PATH

[Install]
WantedBy=cryptsetup-pre.target
""".lstrip()

PACMAN_PACKAGE_NAMES = [
  'linux', 'linux-neptune-61', 'linux-hardened', 'linux-lts', 'linux-rt',
  'linux-rt-lts', 'linux-firmware', 'linux-firmware-neptune',
  'linux-firmware-amdgpu', 'linux-firmware-atheros', 'linux-firmware-broadcom',
  'linux-firmware-cirrus', 'linux-firmware-intel', 'linux-firmware-mediatek',
  'linux-firmware-nvidia', 'linux-firmware-other', 'linux-firmware-radeon',
  'linux-firmware-realtek', 'amd-ucode', 'intel-ucode', 'systemd',
  'edk2-shell', 'tpm2-tools', 'cryptsetup',
]

PACMAN_BEFORE_HOOK_PATH = '/etc/pacman.d/hooks/98-auto_tpm_encrypt.hook'
PACMAN_BEFORE_HOOK_TEMPLATE = """
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
$TARGETS

[Action]
Description = Load modules needed to update the EFI bin and reseal the encryption key
When = PreTransaction
Exec = /bin/sh -c 'modprobe -a tpm_crb vfat'
""".lstrip()

PACMAN_HOOK_PATH = '/etc/pacman.d/hooks/99-auto_tpm_encrypt.hook'
PACMAN_HOOK_TEMPLATE = """
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
$TARGETS

[Action]
Description = Update EFI bin and reseal encryption key
When = PostTransaction
Exec = $script_cmd
""".lstrip()

ALL_HOOK_RELATED_PATHS = (
  INSTALL_HOOK_PATH, RUN_HOOK_PATH,
  UNSEAL_SCRIPT_PATH, UNSEAL_SERVICE_PATH,
  PACMAN_BEFORE_HOOK_PATH, PACMAN_HOOK_PATH,
)

WINDOWS_BOOT_MANAGER_LABELS = ('Windows Boot Manager',)

try:
  import pwd
  ROOT_HOME = pwd.getpwuid(0).pw_dir
except (ModuleNotFoundError, KeyError):
  ROOT_HOME = '/root'

XDG_DATA_HOME = os.path.join(ROOT_HOME, '.local', 'share')
XDG_STATE_HOME = os.path.join(ROOT_HOME, '.local', 'state')
if getattr(os, 'getuid', str)() == 0:
  XDG_DATA_HOME = os.environ.get('XDG_DATA_HOME', XDG_DATA_HOME)
  XDG_STATE_HOME = os.environ.get('XDG_STATE_HOME', XDG_STATE_HOME)

BIN_PATH = os.path.join(ROOT_HOME, '.local', 'bin', 'auto_tpm_encrypt')
FIRMWARE_AUDIT_SCRIPT_PATH = os.path.join(XDG_DATA_HOME, 'auto_tpm_encrypt', 'firmware_audit.py')
DATA_DIR = os.path.join(XDG_DATA_HOME, 'auto_tpm_encrypt')

def die(reason):
  sys.stderr.write(reason + '\n')
  sys.stderr.flush()
  sys.exit(-1)

def natsorted(lst):
  return sorted(lst, key = lambda i: [int(j) if j.isdigit() else j for j in re.split(r'(\d+)', i)])

def atomic_rename_without_overwriting(src, dst):
  open(dst, 'x').close()
  shutil.move(src, dst)

def get_named_arg(name):
  if name not in sys.argv:
    return None
  try:
    return sys.argv[sys.argv.index(name)+1]
  except IndexError:
    die(name + ': argument missing value')

def is_steamos():
  return re.match(r'[\d\.\-]+valve[\d\.\-]+neptune[\d\.\-]*$', platform.release()) is not None

def is_chroot_steamos(root = '/'):
  return os.path.exists(os.path.join(root, 'bin/steamos-readonly'))

@functools.cache
def is_steamos_readonly():
  if not is_chroot_steamos():
    die('is_steamos_readonly called on non-SteamOS root')
  proc = subprocess.run(['steamos-readonly', 'status'], capture_output = True)
  if proc.returncode not in (0,1):
    die(str(proc.returncode) + ': unexpected returncode for is_steamos_readonly')
  return not proc.returncode

@functools.cache
def get_partition_for_mountpoint(mpoint):
  try:
    with open('/proc/mounts', 'r') as f:
      for line in f:
        sp = line.split()
        if sp[1] == mpoint:
          return sp[0]
  except FileNotFoundError:
    return None

@functools.cache
def get_partitions():
  partitions = {}
  js = json.loads(subprocess.check_output(['lsblk', '--json', '--output-all']))
  for device in js['blockdevices']:
    for child in device.get('children', ()):
      partitions[child['path']] = child
  return partitions

def clear_partition_cache():
  subprocess.run(['partprobe'], check = False)
  subprocess.run(['udevadm', 'trigger'], check = True)
  get_partitions.cache_clear()

def get_esp_partitions():
  result = {}
  for path, partition in get_partitions().items():
    if str(partition.get('parttype')).lower() == ESP_GUID:
      result[path] = partition
  return result

def get_or_create_data_dir():
  if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print('Created Data Directory:', DATA_DIR)
  return DATA_DIR

def get_or_create_state_dir():
  path = os.path.join(XDG_STATE_HOME, 'auto_tpm_encrypt')
  if not os.path.exists(path):
    os.makedirs(path)
    print('Created State Directory:', path)
  return path

def guess_steamos_second_stage_efi_partitions_from_esp(esp_part):
  result = []
  expected_prefix = re.sub(r'\d+$', '', esp_part)
  for path, partition in get_partitions().items():
    if (path.startswith(expected_prefix) and
        partition['parttype'].lower() == BASIC_DATA_GUID and
        partition['label'] == 'efi' and
        partition['partlabel'] in ('efi-A', 'efi-B')):
      result.append(path)
  return result

def get_partition_stats_for_mountpoint(mpoint):
  for partition in get_partitions().values():
    if mpoint in partition['mountpoints']:
      return partition
    if 'children' in partition:
      for child in partition['children']:
        if mpoint in child['mountpoints']:
          return partition

def get_partition_stats_via_blkid():
  proc = subprocess.run(['blkid', '-c', '/dev/null'], capture_output=True, check=True)
  results = {}
  for line in proc.stdout.decode().splitlines():
    path = line[:line.index(':')]
    stats = {k:v for k,v in re.findall(r'([\w]+)="(.+?)"', line)}
    results[path] = stats
    try:
      p = os.readlink(path)
      path = os.path.abspath(os.path.join(os.path.dirname(path), p))
      results[path] = stats
    except OSError:
      pass
  return results

def get_filesystem_size(path):
  fstype = get_partitions()[path]['fstype']
  if fstype in ('ext2', 'ext3', 'ext4'):
    proc = subprocess.run(['dumpe2fs', '-h', path], capture_output = True, check = True)
    stats = {}
    for line in map(bytes.decode, proc.stdout.splitlines()):
      try:
        stats[line.split(':')[0].lower()] = int(line.strip().split()[-1])
      except (ValueError, IndexError):
        pass
    return stats['block count'] * stats['block size']
  else:
    die(fstype + ': Unsupported file system on ' + path)

def die_if_not_on_ac_power():
  on_ac_power = False
  checked = False
  for i in os.listdir('/sys/class/power_supply'):
    try:
      with open('/sys/class/power_supply/'+i+'/type', 'r') as f:
        typ = f.read().strip()
      if typ == 'Mains':
        with open('/sys/class/power_supply/'+i+'/online', 'r') as f:
          checked = True
          if f.read().strip() == '1':
            on_ac_power = True
    except FileNotFoundError:
      pass
  if not checked and not os.environ.get('IGNORE_MISSING_AC_STATE'):
    die('Could not check AC state')
  if not on_ac_power:
    msg = 'Not plugged in. Connect your device to its charger.'
    print(msg) if os.environ.get('IGNORE_IF_ON_BATTERY') else die(msg)

def toggle_wakelock(enabled, original_states = None):
  out = subprocess.run(['systemctl', 'list-unit-files'], capture_output = True, check = True)
  states = {sp[0]: sp[1] for sp in filter(lambda i: len(i) == 3, (i.split() for i in out.stdout.decode().splitlines()))}
  if enabled:
    services_to_mask = []
    for service in WAKELOCK_SERVICES:
      if service not in states:
        die(service + ': Service missing when enabling wakelock')
      if states[service] != 'masked':
        services_to_mask.append(service)
    if len(services_to_mask) > 0:
      subprocess.run(['systemctl', 'mask'] + services_to_mask, check = True)
  else:
    services_to_unmask = []
    for service in WAKELOCK_SERVICES:
      if service not in states:
        die(service + ': Service missing when disabling wakelock')
      if original_states[service] != 'masked' and states[service] == 'masked':
        services_to_unmask.append(service)
    if len(services_to_unmask) > 0:
      subprocess.run(['systemctl', 'unmask'] + services_to_unmask, check = True)
  return states

def ensure_pacman_ready_on_steamos():
  # assume pacman is already setup if readonly has been disabled
  if is_chroot_steamos() and is_steamos_readonly():
    print('Making SteamOS root writable')
    subprocess.run(['steamos-readonly', 'disable'], check = True)
    is_steamos_readonly.cache_clear()

    print('Initialize pacman keyring')
    subprocess.run(['pacman-key', '--init'], check = True)

    print('Populating pacman keyring with archlinux signatures')
    subprocess.run(['pacman-key', '--populate'], check = True)

def ensure_command_exists(command, package):
  if shutil.which(command):
    return
  if not shutil.which('pacman'):
    die(command + ' is unavailable and cannot be installed as pacman is also unavailable')
  ensure_pacman_ready_on_steamos()
  if subprocess.run(['pacman', '--needed', '--noconfirm', '-Syu', package]).returncode != SUCCESS:
    die(package + ': pacman failed to install package')

def ensure_packages_that_are_used_in_chroot_are_installed():
  ensure_command_exists('objcopy', 'binutils')
  ensure_command_exists('mkinitcpio', 'mkinitcpio')
  ensure_command_exists('tpm2_unseal', 'tpm2-tools')
  ensure_command_exists('btrfs', 'btrfs-progs')
  if should_use_secure_boot_signing():
    ensure_command_exists('sbsign', 'sbsigntools')

  for cmd in ('lsblk', 'blkid', 'udevadm', 'mount', 'umount'):
    if not shutil.which(cmd):
      die(cmd + ' not found')

def kernel_arg_index(args, arg):
  try:
    return args.index(arg)
  except ValueError:
    pass
  for i, a in enumerate(args):
    if a.startswith(arg+'='):
      return i
  raise ValueError(arg + ' not in kernel args')

def remove_kernel_arg(args, arg):
  while True:
    try:
      del args[kernel_arg_index(args, arg)]
    except ValueError:
      return

def hash_file(path):
  hash = hashlib.sha256()
  with open(path, 'rb') as f:
    while True:
      buf = f.read(64*1024)
      if not buf:
        break
      hash.update(buf)
  return hash.hexdigest()

def capture_current_esp_manifest(esp_root):
  esp_root_with_trailing_sep = esp_root if esp_root.endswith(os.path.sep) else (esp_root+os.path.sep)
  manifest = {}
  for root, dirs, files in os.walk(esp_root):
    for name in files:
      full_path = os.path.join(root, name)
      assert full_path.startswith(esp_root_with_trailing_sep)
      manifest[full_path[len(esp_root_with_trailing_sep):]] = hash_file(full_path)
    for name in dirs:
      full_path = os.path.join(root, name)
      assert full_path.startswith(esp_root_with_trailing_sep)
      manifest[full_path[len(esp_root_with_trailing_sep):]] = None
  return manifest

def load_esp_manifests(manifest_path):
  try:
    with open(os.path.expanduser(manifest_path), 'r') as f:
      manifests = json.load(f)
      if type(manifests) is not dict or any((type(i) is not dict for i in manifests.values())):
        die('Unexpected data in esp manifests')
      return manifests
  except FileNotFoundError:
    return {}

def get_last_esp_manifest(esp_manifests):
  if len(esp_manifests) > 0:
    latest_time = sorted(map(float, esp_manifests.keys()), reverse=True)[0]
    return esp_manifests[str(latest_time)]

def update_esp_manifest_if_changed(esp_root, manifest_path):
  print('Checking if ESP changed')
  current_esp_manifest = capture_current_esp_manifest(esp_root)
  esp_manifests = load_esp_manifests(manifest_path)
  last_esp_manifest = get_last_esp_manifest(esp_manifests)
  if last_esp_manifest != current_esp_manifest:
    print('Recording updated ESP in manifest')
    esp_manifests[time.time()] = current_esp_manifest
    with open(os.path.expanduser(manifest_path), 'w') as f:
      json.dump(esp_manifests, f)
  else:
    print('No change to ESP')

def esp_matches_manifest(esp_root, manifest_path):
  current_esp_manifest = capture_current_esp_manifest(esp_root)
  esp_manifests = load_esp_manifests(manifest_path)
  last_esp_manifest = get_last_esp_manifest(esp_manifests)
  return current_esp_manifest == last_esp_manifest

@functools.cache
def get_device_model():
  try:
    with open('/sys/devices/virtual/dmi/id/board_vendor', 'r') as f:
      board_vendor = f.read().strip()
  except FileNotFoundError:
    board_vendor = 'Unknown'

  try:
    with open('/sys/devices/virtual/dmi/id/board_name', 'r') as f:
      board_name = f.read().strip()
  except FileNotFoundError:
    board_name = 'Unknown'

  return board_vendor + ' ' + board_name

def device_is_steamdeck():
  return get_device_model() == 'Valve Jupiter'

def should_use_secure_boot_signing():
  return (
    USE_SECURE_BOOT_SIGNING and
    not device_is_steamdeck() and
    get_named_arg('--key') is not None and
    get_named_arg('--cert') is not None)

def maybe_kill_windows_boot_manager():
  if not SHOULD_KILL_WINDOWS_BOOT_MANAGER:
    return
  efibootmgr = shutil.which('efibootmgr')
  if not efibootmgr:
    die('efibootmgr is missing')
  for label in WINDOWS_BOOT_MANAGER_LABELS:
    print(
      'Trying to kill Windows Boot Manager with label {}'.format(repr(label))
    )
    proc = subprocess.run((efibootmgr, '--label', label, '--delete-bootnum'))
    print('  Return Code: ' + str(proc.returncode))

def print_sys_info_and_do_sanity_checks():
  model = get_device_model()
  root_partition = get_partition_for_mountpoint('/')
  home_partition = get_partition_for_mountpoint('/home')
  var_partition = get_partition_for_mountpoint('/var')

  print('OS:', platform.release())
  print('SteamOS:', 'yes' if is_steamos() else 'no')
  print('Device:', model)
  print('Root Partition:', root_partition)
  print('Home Partition:', home_partition)
  print('Var Partition:', var_partition)
  print('')

  if platform.system() != 'Linux':
    die('Script must be run on Linux')

  if os.geteuid() != 0:
    die('Script must be run as root')

  nvme_namespaces = list(filter(lambda i: re.match(r'nvme\d+n\d+$', i), os.listdir('/dev')))
  if device_is_steamdeck() and len(nvme_namespaces) != 1:
    die('Expected 1 nvme namespace, found ' + str(len(nvme_namespaces)))

  sd_cards = list(filter(lambda i: re.match(r'mmcblk\d+$', i), os.listdir('/dev')))
  if device_is_steamdeck() and len(sd_cards) != 1:
    die('Expected 1 sd card, found ' + str(len(sd_cards)) + '. Please re-read the guide.')

  drives = list(filter(lambda i: re.match('sd[a-z]+$', i), os.listdir('/dev')))
  if device_is_steamdeck() and len(drives) != 0:
    die('Expected 0 drives, found ' + str(len(sd_cards)) + '. Please eject all USB storage devices.')

  if not root_partition:
    die('Could not determine root partition')

  if device_is_steamdeck() and not re.match(r'^/dev/(nvme\d+n\d+p\d+|mmcblk\d+p\d+|mapper/\w+)', root_partition):
    die('Root was mounted from an unsupported device')

  die_if_not_on_ac_power()

  for cmd in ('lsblk', 'mount', 'umount', 'resize2fs', 'e2fsck', 'dumpe2fs', 'modprobe', 'systemctl'):
    if not shutil.which(cmd):
      die(cmd + ' not found')

  if SHOULD_KILL_WINDOWS_BOOT_MANAGER:
    ensure_command_exists('efibootmgr', 'efibootmgr')

  ensure_command_exists('cryptsetup', 'cryptsetup')
  ensure_command_exists('arch-chroot', 'arch-install-scripts')
  ensure_command_exists('partprobe', 'parted')
  ensure_command_exists('btrfs', 'btrfs-progs')

  ensure_packages_that_are_used_in_chroot_are_installed()

  nvme_esp_partitions = list(filter(lambda i: re.match(r'/dev/nvme\d+n\d+p\d+$', i), get_esp_partitions().keys()))
  if device_is_steamdeck() and len(nvme_esp_partitions) != 1:
    die('Expected 1 nvme esp partition, found ' + str(len(nvme_esp_partitions)))

  mmc_esp_partitions = list(filter(lambda i: re.match(r'/dev/mmcblk\d+p\d+$', i), get_esp_partitions().keys()))
  if device_is_steamdeck() and len(mmc_esp_partitions) != 1:
    die('Expected 1 mmc esp partition, found ' + str(len(mmc_esp_partitions)))

  if subprocess.run(['modprobe', 'tpm']).returncode != SUCCESS:
    if os.path.exists('/efi/EFI/steamos/grub.cfg'):
      with open('/efi/EFI/steamos/grub.cfg', 'r+') as f:
        cfg = f.read()
        if ' module_blacklist=tpm ' in cfg:
          cfg = cfg.replace(' module_blacklist=tpm ', ' ')
          f.seek(0)
          f.write(cfg)
          f.truncate()
          print('The TPM module cannot be loaded due to your current kernel args')
          print('grub.cfg has been modified to unblock the module')
          print('Please reboot and re-run this script')
    die('Error loading TPM kernel module')

  if subprocess.run(['modprobe', 'dm_crypt']).returncode != SUCCESS:
    die('Error loading dm_crypt kernel module')

  if os.path.exists('/dev/mapper/current_tpm_encrypted_vol'):
    die('/dev/mapper/current_tpm_encrypted_vol already exists')

  suffix = get_named_arg('--suffix')
  if suffix and ' ' in suffix:
    die('suffix must not contain any spaces')

  pcrs = list(map(str.strip, PCR_LIST.split(',')))
  for pcr in pcrs:
    if not pcr.isdigit():
      die(f'Invalid PCR: {pcr}')
    pcr = int(pcr)
    if pcr < 0 or pcr > 23:
      die(f'Invalid PCR: {pcr}')
  if ','.join(map(str,map(int,pcrs))) != PCR_LIST:
    die(f'Invalid PCR List: {PCR_LIST}')

def print_esp_partitions():
  print('Available ESP partitions are:')
  for path, stats in get_esp_partitions().items():
    print(' ', path, stats['fsver'], stats['size'])
  print('')

  print('Note: The ESP partition should be on the same device as the other partitions.')
  print('')

def get_existing_tpm_address_from_hooks(root='/'):
  for path in (os.path.join(root, p[1:]) for p in (UNSEAL_SCRIPT_PATH, RUN_HOOK_PATH)):
    try:
      with open(path, 'r') as f:
        existing_hook = f.read()
      try:
        return re.search(r'tpm2_unseal -c (0x[a-f0-9]+)', existing_hook).group(1)
      except AttributeError:
        die('Seal address missing from existing hook. Ensure you are running the latest version of this script.')
    except FileNotFoundError:
      pass

def die_if_no_usable_tpm_slots(root = '/'):
  existing_address = get_existing_tpm_address_from_hooks(root = root)
  if existing_address:
    return
  proc = subprocess.run(['tpm2_getcap', 'properties-variable'], capture_output = True, check = True)
  match = re.search(r'TPM2_PT_HR_PERSISTENT_AVAIL:\s*0x([0-9A-Fa-f])', proc.stdout.decode())
  if not match:
    die('TPM2 properties missing available persistent slot count')
  free_slots = int(match.group(1), base = 16)
  if free_slots < 1:
    die('No free slots to store sealed key. Free up some space before re-running the script.')

def remove_blank_password(partition):
  while True:
    proc = subprocess.run(['cryptsetup', 'luksRemoveKey', partition], input = BLANK_PASSWORD + b'\n')
    if proc.returncode not in (SUCCESS, PASSPHRASE_NOT_FOUND):
      die(str(proc.returncode) + ': Failed to remove blank password on ' + partition)
    elif proc.returncode == PASSPHRASE_NOT_FOUND:
      return

def ensure_file_has_desired_contents(path, desired_contents, mode = None):
  try:
    with open(path, 'r+') as f:
      old_contents = f.read()
      if old_contents != desired_contents:
        print('Updating ' + path + '...')
        f.seek(0)
        f.write(desired_contents)
        if len(desired_contents) < len(old_contents):
          f.truncate()
  except FileNotFoundError:
    print('Creating ' + path + '...')
    os.makedirs(os.path.dirname(path), mode = 0o755, exist_ok = True)
    with open(path, 'x') as f:
      f.write(desired_contents)
  if mode is not None:
    os.chmod(path, mode)

def encrypt(root_partition, home_partition, var_partition, esp_partition):
  tmp_mountpoint = tempfile.mkdtemp(prefix='tmp_mountpoint_')

  print('Checking tpm slots')
  subprocess.run(['mount', root_partition, tmp_mountpoint], check = True)
  die_if_no_usable_tpm_slots(root = tmp_mountpoint)
  subprocess.run(['umount', tmp_mountpoint], check = True)

  print('Generating encryption key')
  getrandom = getattr(os, 'getrandom', None)
  grnd_random = getattr(os, 'GRND_RANDOM', 0)
  encryption_key = b''
  while len(encryption_key) < KEY_LENGTH_IN_BYTES:
    if getrandom and grnd_random:
      encryption_key += getrandom(1, flags = grnd_random)
    else:
      encryption_key = os.urandom(1)

  print('Storing backup of key')
  while True:
    key_backup_path = os.path.join(get_or_create_data_dir(),
                                   'secret-backup.' + os.urandom(4).hex() + '.bin')
    try:
      f = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
      f = os.open(key_backup_path, f, mode = 0o600)
      with open(f, 'xb') as f:
        f.write(encryption_key)
      print('Backup stored at ' + key_backup_path)
      break
    except FileExistsError:
      pass

  files_to_backup = [key_backup_path]
  header_backup_dir = tempfile.mkdtemp(prefix='luks_header_backups_')

  if USE_ESP_MANIFEST:
    print('Mounting partition to update ESP manifest')
    subprocess.run(['mount', esp_partition, tmp_mountpoint], check = True)
    manifest_path = os.path.join(get_or_create_state_dir(), ESP_MANIFEST_PATH)
    update_esp_manifest_if_changed(tmp_mountpoint, manifest_path)
    subprocess.run(['umount', tmp_mountpoint], check = True)
    files_to_backup.append(os.path.expanduser(manifest_path))

  if USE_STEAMOS_SECOND_STAGE_ESP_MANIFEST:
    print('Mounting partitions to update seconds stage ESP manifests')
    second_stage_esps = guess_steamos_second_stage_efi_partitions_from_esp(esp_partition)
    for second_stage_esp in second_stage_esps:
      manifest_path = os.path.join(
                       get_or_create_state_dir(),
                       (STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX +
                        get_partitions()[second_stage_esp]['partlabel'] +
                        STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_EXTENSION))
      subprocess.run(['mount', second_stage_esp, tmp_mountpoint], check = True)
      update_esp_manifest_if_changed(tmp_mountpoint, manifest_path)
      subprocess.run(['umount', tmp_mountpoint], check = True)
      files_to_backup.append(os.path.expanduser(manifest_path))

  for partition in (var_partition, home_partition, root_partition):
    if partition:
      if partition == var_partition:
        print('Mounting {} to clear swapfile'.format(partition))
        subprocess.run(['mount', partition, tmp_mountpoint])

        try:
          with open(os.path.join(tmp_mountpoint, 'swapfile'), 'r+') as f:
            print('Clearing swapfile on {}'.format(partition))
            f.truncate(0)
        except FileNotFoundError:
          pass

      print('Unmounting', partition)
      proc = subprocess.run(['umount', '--all-targets', partition])
      if proc.returncode not in (SUCCESS, ALREADY_UNMOUNTED):
        die(str(proc.returncode) + ': Unexpected return code when unmounting ' + partition)

      print('Checking', partition)
      fstype = get_partitions()[partition]['fstype']
      if fstype in ('ext2', 'ext3', 'ext4'):
        subprocess.run(['e2fsck', '-p', '-f', partition], check = True)
      elif fstype == 'btrfs':
        subprocess.run(['btrfs', 'check', partition], check = True)
      else:
        die(fstype + ': unexpected file system type for ' + partition)

      print('Shrinking file system on', partition)
      die_if_not_on_ac_power()
      if fstype in ('ext2', 'ext3', 'ext4'):
        new_size_in_kb = (get_filesystem_size(partition)//1024) - (64*1024)
        if new_size_in_kb < 0:
          die('Selected partition is too small')
        subprocess.run(['resize2fs', partition, str(int(new_size_in_kb))+'K'], check = True)
      elif fstype == 'btrfs':
        subprocess.run(['mount', partition, tmp_mountpoint], check = True)
        subprocess.run(['btrfs', 'filesystem', 'resize', '-64M', tmp_mountpoint], check = True)
        subprocess.run(['umount', tmp_mountpoint], check = True)

      print('Enabling wakelock')
      die_if_not_on_ac_power()
      original_states = toggle_wakelock(True)

      maybe_kill_windows_boot_manager()

      # TODO --progress-json
      print('Encrypting (this may take 2+ hours)', partition)
      subprocess.run(['cryptsetup', 'reencrypt', '--encrypt', partition, '--reduce-device-size', '32M', '--batch-mode'],
                     input = BLANK_PASSWORD + b'\n' + BLANK_PASSWORD + b'\n',
                     check = True)

      print('Adding encryption key to partition', partition)
      subprocess.run(['cryptsetup', 'luksAddKey', partition, key_backup_path], input = BLANK_PASSWORD + b'\n', check = True)

      print('Backing up LUKS header', partition)
      tmp_header_path = os.path.join(header_backup_dir, 'header.bin')
      subprocess.run(['cryptsetup', 'luksHeaderBackup', partition, '--header-backup-file', tmp_header_path], check = True)
      while True:
        header_backup_path = os.path.join(get_or_create_data_dir(),
                                          'header-backup.' + re.sub(r'[^\w]', '_', partition) + '.' + os.urandom(4).hex() + '.bin')
        try:
          atomic_rename_without_overwriting(tmp_header_path, header_backup_path)
          files_to_backup.append(header_backup_path)
          print('Backed up header to ', header_backup_path)
          break
        except FileExistsError:
          pass

      print('Opening encrypted partition', partition)
      subprocess.run(['cryptsetup', 'open', partition, 'current_tpm_encrypted_vol'], input = BLANK_PASSWORD + b'\n', check = True)

      print('Checking encrypted file system', partition)
      if fstype in ('ext2', 'ext3', 'ext4'):
        subprocess.run(['e2fsck', '-p', '-f', '/dev/mapper/current_tpm_encrypted_vol'], check = True)
      elif fstype == 'btrfs':
        subprocess.run(['btrfs', 'check', '/dev/mapper/current_tpm_encrypted_vol'], check = True)

      print('Growing file system', partition)
      if fstype in ('ext2', 'ext3', 'ext4'):
        subprocess.run(['resize2fs', '/dev/mapper/current_tpm_encrypted_vol'], check = True)
      elif fstype == 'btrfs':
        subprocess.run(['mount', '/dev/mapper/current_tpm_encrypted_vol', tmp_mountpoint], check = True)
        subprocess.run(['btrfs', 'filesystem', 'resize', 'max', tmp_mountpoint], check = True)
        subprocess.run(['umount', tmp_mountpoint], check = True)

      if partition == root_partition:
        print('Mounting the encrypted root partition')
        clear_partition_cache()
        mount_point = tempfile.mkdtemp(prefix='tmp_root_')
        subprocess.run(['mount', '/dev/mapper/current_tpm_encrypted_vol', mount_point], check = True)

        if fstype == 'btrfs':
          subprocess.run(['btrfs', 'property', 'set', tmp_mountpoint, 'ro', 'false'], check = True)
          # TODO: retry in loop with timeout

        print('Copying encryption key to partition')
        while True:
          try:
            partition_key_path = os.path.join(mount_point, 'secret.bin')
            with open(partition_key_path, 'xb') as f:
              f.write(encryption_key)
            os.chmod(partition_key_path, stat.S_IRWXU | stat.S_IRWXG)
            break
          except FileExistsError:
            try:
              old_key_path = os.path.join(mount_point, 'secret.' + os.urandom(4).hex() + '.bin')
              atomic_rename_without_overwriting(partition_key_path, old_key_path)
              print('Moved existing key to ', old_key_path)
            except FileExistsError:
              pass

        print('Checking if local copy of this script exists in encrypted partition')
        with open(__file__, 'r') as f:
          script_code = f.read()
        ensure_file_has_desired_contents(
          os.path.join(mount_point, BIN_PATH[len(os.path.sep):]),
          script_code,
          mode = stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC,
        )

        print('Setting up TPM auto encrypt via copied script')
        args = ['--setup_auto_tpm_decrypt', '--esp', esp_partition]
        if home_partition:
          args += ['--home', home_partition]
        if var_partition:
          args += ['--var', var_partition]
        for i in ('suffix', 'key', 'cert'):
          val = get_named_arg('--'+i)
          if val:
            args += ['--'+i, val]

        exe = os.path.basename(sys.executable)
        subprocess.run(['arch-chroot', mount_point, exe, BIN_PATH] + args, check = True)

        print('Disabling wakelock')
        toggle_wakelock(False, original_states = original_states)

        print('Unmounting the encrypted partition')
        subprocess.run(['umount', mount_point], check = True)

      print('Closing encrypted partition', partition)
      subprocess.run(['cryptsetup', 'close', '/dev/mapper/current_tpm_encrypted_vol'], check = True)

  print('Done! See the guide for next steps.')
  print('Make sure you move your backups somewhere secure:')
  for file in files_to_backup:
    print(' ', file)


def decrypt(root_partition, home_partition, var_partition, esp_partition, key_file=None):
  if not key_file:
    print('Enter the path of the key file:')
    key_file = input('> ')
    print('')

  if not os.path.isfile(key_file):
    die('Key not found')

  if not SKIP_CONTROLLER_FIRMWARE_AUDIT and \
     os.path.exists(FIRMWARE_AUDIT_SCRIPT_PATH) and \
     is_steamos():
    print('Running controller firmware audit')
    subprocess.run([sys.executable, FIRMWARE_AUDIT_SCRIPT_PATH], check=True)

  print('Unmounting', root_partition)
  die_if_not_on_ac_power()
  proc = subprocess.run(['umount', '--all-targets', root_partition])
  if proc.returncode not in (SUCCESS, ALREADY_UNMOUNTED):
    die(str(proc.returncode) + ': Unexpected return code when unmounting ' + partition)

  print('Opening', root_partition)
  subprocess.run(['cryptsetup', 'open', root_partition, 'current_tpm_encrypted_vol', '--key-file', key_file], check = True)

  print('Mounting', root_partition)
  tmp_root = tempfile.mkdtemp(prefix='tmp_root_')
  subprocess.run(['mount', '/dev/mapper/current_tpm_encrypted_vol', tmp_root], check = True)

  print('Checking OS and unmounting')
  part_is_steamos = is_chroot_steamos(root=tmp_root)
  subprocess.run(['umount', tmp_root], check = True)

  print('Closing')
  subprocess.run(['cryptsetup', 'close', 'current_tpm_encrypted_vol'], check = True)

  if part_is_steamos:
    print('OS is SteamOS')
  else:
    print('OS is not SteamOS')

  print('Enabling wakelock')
  die_if_not_on_ac_power()
  original_states = toggle_wakelock(True)

  for partition in (root_partition, home_partition, var_partition):
    if partition:
      print('Removing blank password if added')
      remove_blank_password(partition)

      # NB: Workaround for the LUKS attached header decryption bug
      #     See https://wiki.archlinux.org/title/Removing_system_encryption#Decrypting_LUKS2_devices_in-place
      #     This workaround can be removed once it's confirmed that newer versions of SteamOS ship without the bug
      #     albeit at the cost of breaking backwards compatibility with older versions of SteamOS
      print('Enumerating LUKS keyslots')
      proc = subprocess.run(['cryptsetup', 'luksDump', partition], check = True, capture_output = True)
      if proc.returncode != SUCCESS:
        die(partition + ': Failed to dump LUKS header')
      keyslots = re.findall(r'(\d+):[^\n]+\n\s*Key:', proc.stdout.decode())
      if len(keyslots) < 1:
        die('No keyslots found')

      die_if_not_on_ac_power()
      for keyslot in keyslots:
        print('Converting keyslot', keyslot, partition)
        proc = subprocess.run(['cryptsetup', 'luksConvertKey', '--key-slot', keyslot, '--pbkdf', 'pbkdf2', '--key-file', key_file, partition])
        if proc.returncode == PASSPHRASE_NOT_FOUND:
          die('A key not setup by this script was found. Remove all custom keys, close the device and try again.')
        if proc.returncode != SUCCESS:
          die(str(proc.returncode) + ': Unexpected error code when converting key slot ' + keyslot + ' on ' + partition)

      print('Converting partition to luks1', partition)
      subprocess.run(['cryptsetup', 'convert', '--type', 'luks1', '--batch-mode', partition], check = True)

      print('Decrypting (this may take 2+ hours)', partition)
      if shutil.which('cryptsetup-reencrypt'):
        subprocess.run(['cryptsetup-reencrypt', '--key-file', key_file, '--decrypt', partition], check = True)
      else:
        subprocess.run(['cryptsetup', 'reencrypt', '--key-file', key_file, '--decrypt', partition], check = True)

      print('Waiting for file system to become available and checking file system type')
      for _ in range(math.ceil(FILESYTEM_WAIT_TOTAL_TIME/FILESYTEM_WAIT_ITERATION_TIME)):
        time.sleep(FILESYTEM_WAIT_ITERATION_TIME)
        clear_partition_cache()
        fstype = get_partitions()[partition]['fstype']
        if fstype:
          break
      if fstype not in SUPPORTED_UNENCRYPTED_FILESYSTEMS:
        die(partition + ': Decrypted file system has an unsupported type ' + str(fstype))

      print('Unmounting', partition)
      proc = subprocess.run(['umount', '--all-targets', partition])
      if proc.returncode not in (SUCCESS, ALREADY_UNMOUNTED):
        die(str(proc.returncode) + ': Unexpected return code when unmounting ' + partition)

      print('Checking decrypted file system', partition)
      if fstype in ('ext2', 'ext3', 'ext4'):
        subprocess.run(['e2fsck', '-p', '-f', partition], check = True)
      elif fstype == 'btrfs':
        subprocess.run(['btrfs', 'check', partition], check = True)

      print('Growing decrypted file system', partition)
      if fstype in ('ext2', 'ext3', 'ext4'):
        subprocess.run(['resize2fs', partition], check = True)
      elif fstype == 'btrfs':
        subprocess.run(['mount', partition, tmp_root], check = True)
        subprocess.run(['btrfs', 'filesystem', 'resize', 'max', tmp_root], check = True)
        subprocess.run(['umount', tmp_root], check = True)

      if partition == root_partition:
        print('Mounting root', partition)
        subprocess.run(['mount', partition, tmp_root], check = True)

        for tab in ('/etc/fstab', '/etc/crypttab.initramfs'):
          print('Restoring', tab)
          buf = []
          try:
            with open(os.path.join(tmp_root, tab[1:]), 'r+') as f:
              for line in map(str.strip, f):
                if line.startswith(REMOVED_COMMENT):
                  buf.append(line[len(REMOVED_COMMENT):])
                elif line.endswith(ADDDED_COMMENT):
                  pass
                else:
                  buf.append(line)
              f.seek(0)
              f.write('\n'.join(buf) + '\n')
              f.truncate()
          except FileNotFoundError:
            pass

        print('Checking if a sealed key exists')
        key_address = get_existing_tpm_address_from_hooks(root = tmp_root)
        if key_address:
          print('Key found, evicting')
          proc = subprocess.run(['tpm2_evictcontrol', '--hierarchy', TPM_RH_OWNER, '--object-context', key_address])
          if proc.returncode != SUCCESS:
            die(str(proc.returncode) + ': Unexpected return code when evicting old sealed key')
        else:
          print('No key found')

        print('Removing hooks and associated scripts')
        for path in ALL_HOOK_RELATED_PATHS:
          try:
            os.remove(os.path.join(tmp_root, path[1:]))
          except FileNotFoundError:
            pass

        if DO_MASK_STEAMCL_SERVICE:
          print('Re-enabling SteamCL installer')
          try:
            os.unlink(os.path.join(tmp_root, STEAMCL_SERVICE_MASK_PATH[1:]))
          except FileNotFoundError:
            pass

        print('Unmounting root', partition)
        subprocess.run(['umount', tmp_root], check = True)

  print('Disabling wakelock')
  toggle_wakelock(False, original_states = original_states)

  esp_warning = ('WARNING! The contents of your ESP do not match what was recorded\n' +
                 '         in the manifest. It is possible your ESP has been\n' +
                 '         tampered with and is insecure! Proceed carefully.\n' +
                 '         See the guide for details. Press enter to continue.\n')

  die_reason = None
  if part_is_steamos or USE_ESP_MANIFEST:
    print('Mounting ESP partition')
    subprocess.run(['mount', esp_partition, tmp_root], check = True)

    if part_is_steamos:
      print('Restoring chainloader')
      try:
        shutil.copy2(os.path.join(DATA_DIR, 'bootx64.original.efi'),
                     os.path.join(tmp_root, 'efi/boot/bootx64.efi'))
      except FileNotFoundError:
        die_reason = 'Could not restore chainloader (bootx64). Chainloader backup missing.'

      try:
        shutil.copy2(os.path.join(DATA_DIR, 'steamcl.original.efi'),
                     os.path.join(tmp_root, 'efi/steamos/steamcl.efi'))
      except FileNotFoundError:
        die_reason = 'Could not restore chainloader (steamcl). Chainloader backup missing.'

    if USE_ESP_MANIFEST:
      print('Verifying ESP against manifest for', esp_partition)
      if not esp_matches_manifest(tmp_root, ESP_MANIFEST_PATH):
        print(esp_warning)
        input('')

    print('Unmount ESP partition')
    subprocess.run(['umount', tmp_root], check = True)

  if part_is_steamos and USE_STEAMOS_SECOND_STAGE_ESP_MANIFEST:
    second_stage_esps = guess_steamos_second_stage_efi_partitions_from_esp(esp_partition)
    for second_stage_esp in second_stage_esps:
      print('Verifying ESP against manifest for', esp_partition)
      subprocess.run(['mount', second_stage_esp, tmp_root], check = True)
      manifest_path = (STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX +
                       get_partitions()[second_stage_esp]['partlabel'] +
                       STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_EXTENSION)
      if not esp_matches_manifest(tmp_root, manifest_path):
        print(esp_warning)
        input('')
      subprocess.run(['umount', tmp_root], check = True)

  if die_reason:
    die(die_reason)

  print('Done')

def encrypt_or_decrypt():
  die_if_not_on_ac_power()
  print('Enter the root partition to encrypt or decrypt:')
  root_partition = input('> ')
  print('')

  if not root_partition:
    die('Root partition cannot be blank')

  print('Enter the home partition to encrypt or decrypt or leave blank if same as root:')
  home_partition = input('> ')
  print('')

  if home_partition == root_partition:
    die('home and root partition cannot be the same')

  print('Enter the var partition to encrypt or decrypt or leave blank if same as root:')
  var_partition = input('> ')
  print('')

  if var_partition == root_partition:
    die('var and root partition cannot be the same')

  for partition in (root_partition, home_partition, var_partition):
    if partition:
      if partition not in get_partitions():
        die(partition + ': partition path not found')

      if device_is_steamdeck() and not re.match(r'^/dev/(nvme\d+n\d+p\d+|mmcblk\d+p\d+)', partition):
        die(partition + ': partition must be on NVME or SD card')

      if partition == get_partition_for_mountpoint('/'):
        die(partition + ': cannot use mounted root partition')

      if partition == get_partition_for_mountpoint('/home'):
        die(partition + ': cannot use mounted home partition')

      if partition == get_partition_for_mountpoint('/var'):
        die(partition + ': cannot use mounted var partition')

      fstype = get_partitions()[partition]['fstype']
      if fstype not in SUPPORTED_FILESYSTEMS:
        die(fstype + ': unsupported file system in ' + partition)

  root_fstype = get_partitions()[root_partition]['fstype']

  if (home_partition and
      root_fstype in SUPPORTED_ENCRYPTED_FILESYSTEMS and
      get_partitions()[home_partition]['fstype'] not in SUPPORTED_ENCRYPTED_FILESYSTEMS):
      die('root is encrypted but home is already unencrypted')

  if (home_partition and
      root_fstype in SUPPORTED_UNENCRYPTED_FILESYSTEMS and
      get_partitions()[home_partition]['fstype'] not in SUPPORTED_UNENCRYPTED_FILESYSTEMS):
      die('root is unencrypted but home is already encrypted')

  if (var_partition and
      root_fstype in SUPPORTED_ENCRYPTED_FILESYSTEMS and
      get_partitions()[var_partition]['fstype'] not in SUPPORTED_ENCRYPTED_FILESYSTEMS):
      die('root is encrypted but var is already unencrypted')

  if (var_partition and
      root_fstype in SUPPORTED_UNENCRYPTED_FILESYSTEMS and
      get_partitions()[var_partition]['fstype'] not in SUPPORTED_UNENCRYPTED_FILESYSTEMS):
      die('root is unencrypted but var is already encrypted')

  print_esp_partitions()
  print('Select the ESP partition:')
  esp_partition = input('> ')
  print('')

  if esp_partition not in get_esp_partitions() and \
     os.path.abspath(
       os.path.join(os.path.dirname(esp_partition),
                    os.readlink(esp_partition))) not in get_esp_partitions():
    die('Not a valid ESP partition')

  if root_fstype in SUPPORTED_ENCRYPTED_FILESYSTEMS:
    decrypt(root_partition, home_partition, var_partition, esp_partition)
  elif root_fstype in SUPPORTED_UNENCRYPTED_FILESYSTEMS:
    encrypt(root_partition, home_partition, var_partition, esp_partition)
  else:
    die(fstype + ': unsupported file system type')

def get_non_root_partitions_from_hook():
  try:
    with open(PACMAN_HOOK_PATH, 'r') as f:
      hook_data = f.read()
    match = re.search(r'--esp\s(.+?)\s*(--|\n|$)', hook_data)
    if not match:
      die('Unable to load ESP partition from existing hook. Make sure you are running the latest version of this script.')
    esp_partition = match.group(1)
    if '--home' in hook_data:
      match = re.search(r'--home\s(.+?)\s*(--|\n|$)', hook_data)
      if not match:
        die('Unable to load home partition from existing hook. Make sure you are running the latest version of this script.')
      home_partition = match.group(1)
    else:
      home_partition = None
    if '--var' in hook_data:
      match = re.search(r'--var\s(.+?)\s*(--|\n|$)', hook_data)
      if not match:
        die('Unable to load var partition from existing hook. Make sure you are running the latest version of this script.')
      var_partition = match.group(1)
    else:
      var_partition = None
  except FileNotFoundError:
    die('Pacman hook missing. This option can only be run from an already encrypted OS. Please re-read the guide.')
  return esp_partition, home_partition, var_partition

def setup_auto_tpm_decrypt():
  was_autorun = '--setup_auto_tpm_decrypt' in sys.argv

  if was_autorun:
    esp_partition = get_named_arg('--esp')
    home_partition = get_named_arg('--home')
    var_partition = get_named_arg('--var')
    efi_bin_suffix = get_named_arg('--suffix')
    secure_boot_key = get_named_arg('--key')
    secure_boot_cert = get_named_arg('--cert')
  else:
    esp_partition, home_partition, var_partition = get_non_root_partitions_from_hook()

  print('ESP Partition: {}'.format(esp_partition))
  print('Home Partition: {}'.format(home_partition))
  print('Var Partition: {}'.format(var_partition))

  if not esp_partition:
    die('missing esp partition')

  root_stats = get_partition_stats_for_mountpoint('/')
  if not root_stats:
    die('Could not get stats for root')

  root_path = root_stats['path']
  blkid_stats = get_partition_stats_via_blkid()
  root_uuid = blkid_stats[root_path]['UUID']

  ensure_packages_that_are_used_in_chroot_are_installed()
  die_if_no_usable_tpm_slots()

  workspace_dir = tempfile.mkdtemp(prefix='workspace_')

  if was_autorun:
    print('Finding kernel to use for EFI bin')
    kernels_dir = '/usr/lib/modules'
    kernels = natsorted(filter(lambda i: not i.startswith('extramodules-'),
                               os.listdir(kernels_dir)))
    if len(kernels) < 1:
      die('Could not find any kernels')
    kernel_found = False
    for kernel_name in reversed(kernels):
      kernel_bin = os.path.join(kernels_dir, kernel_name, 'vmlinuz')
      if os.path.isfile(kernel_bin):
        print('Selected kernel:', kernel_name)
        kernel_found = True
        break
    if not kernel_found:
      print('Possible kernels: ' + repr(kernels))
      die('Unable to locate kernel binary')

    print('Generating kernel command line args')
    kernel_args = ''
    try:
      with open('/etc/default/grub', 'r') as f:
        grub_defaults = f.read()
      try:
        kernel_args += json.loads(re.search(r'GRUB_CMDLINE_LINUX_DEFAULT\s*=\s*(".*")', grub_defaults).group(1))
      except AttributeError:
        pass
      try:
        kernel_args += ' ' + json.loads(re.search(r'GRUB_CMDLINE_LINUX\s*=\s*(".*")', grub_defaults).group(1))
      except AttributeError:
        pass
    except FileNotFoundError:
      pass

    kernel_args = shlex.split(kernel_args)
    remove_kernel_arg(kernel_args, 'rd.luks')

    if device_is_steamdeck():
      remove_kernel_arg(kernel_args, 'fbcon')

    if is_chroot_steamos():
      remove_kernel_arg(kernel_args, 'module_blacklist')

    if SHOW_KERNEL_MESSAGES_AT_BOOT:
      remove_kernel_arg(kernel_args, 'quiet')
      remove_kernel_arg(kernel_args, 'splash')
      remove_kernel_arg(kernel_args, 'plymouth.ignore-serial-consoles')

    if ENABLE_IOMMU and is_chroot_steamos():
      remove_kernel_arg(kernel_args, 'amd_iommu')

    if device_is_steamdeck():
      kernel_args += ['fbcon=rotate:1']

    if DISABLE_GPT_AUTO:
      kernel_args += ['systemd.gpt_auto=no']

    if USE_SYSTEMD_INIT:
      kernel_args += ['rd.luks.name=' + root_uuid + '=tpm_encrypted_root', 'root=/dev/mapper/tpm_encrypted_root']
      if home_partition:
        kernel_args += ['rd.luks.name=' + blkid_stats[home_partition]['UUID'] + '=tpm_encrypted_home']
      if var_partition:
        kernel_args += ['rd.luks.name=' + blkid_stats[var_partition]['UUID'] + '=tpm_encrypted_var']
      if RD_LUKS_TIMEOUT is not None or RD_LUKS_TRY_EMPTY_PASSWORD or RD_LUKS_NO_READ_WORKQUEUE:
        options = []
        if RD_LUKS_TIMEOUT is not None:
          options += ['timeout=' + str(RD_LUKS_TIMEOUT)]
        if RD_LUKS_TRY_EMPTY_PASSWORD:
          options += ['try-empty-password']
        if RD_LUKS_NO_READ_WORKQUEUE:
          options += ['no-read-workqueue']
        kernel_args += ['rd.luks.options=' + ','.join(options)]
    else:
      kernel_args += ['cryptdevice=UUID=' + blkid_root_stats['UUID'] + ':tpm_encrypted_root', 'root=/dev/mapper/tpm_encrypted_root']

    kernel_args = shlex.join(kernel_args)
    kernel_args_path = os.path.join(workspace_dir, 'kernel_cmdline.txt')
    with open(kernel_args_path, 'w') as f:
      f.write(kernel_args)
    print('Kernel cmdline:', kernel_args)

  print('Finding a free address to seal the key')
  tpm_address = get_existing_tpm_address_from_hooks()
  need_to_evict_old_key = (tpm_address is not None)
  if not tpm_address:
    possible_addresses = set((hex(i) for i in range(0x81000000, 0x81000100)))
    proc = subprocess.run(['tpm2_getcap', 'handles-persistent'], check = True, capture_output = True)
    if proc.returncode != SUCCESS:
      die('Unable to check existing persistent TPM handles')
    in_use_addresses = set(re.findall('0x[a-f0-9]+', proc.stdout.decode().lower()))
    free_addresses = possible_addresses - in_use_addresses
    if len(free_addresses) < 1:
      die('No free persistent TPM handles! See the guide for help.')
    tpm_address = sorted(free_addresses)[0]
  print('Using TPM address', tpm_address)

  print('Determining PCR hash algorithm')
  proc = subprocess.run(['tpm2_pcrread'], capture_output = True)
  if proc.returncode != SUCCESS:
    die('Failed to read PCRs')
  supported_hash_algs = sorted(
    set(re.findall(r'(\w+):\s*\n\s+0\s:',
                   proc.stdout.decode())
    ).union(('sha1','sha256')),
    reverse=True,
  )
  if len(supported_hash_algs) < 1:
    die('None of the hash algorithms supported by this TPM are supported by this script')
  hash_algorithm = supported_hash_algs[0]

  if need_to_evict_old_key:
    print('Removing the existing key')
    proc = subprocess.run(['tpm2_evictcontrol', '--hierarchy', TPM_RH_OWNER, '--object-context', tpm_address])
    if proc.returncode not in (SUCCESS, HANDLE_NOT_FOUND):
      die(str(proc.returncode) + ': Unexpected return code when removing old sealed key')

  print('Sealing the key')
  subprocess.run(['tpm2_createpolicy',
                    '--quiet',
                    '--policy-pcr',
                    '--pcr-list', hash_algorithm+':'+PCR_LIST,
                    '--policy', os.path.join(workspace_dir, 'policy.digest')], check=True)
  subprocess.run(['tpm2_createprimary',
                    '--quiet',
                    '--key-context', os.path.join(workspace_dir, 'primary.context')], check=True)
  subprocess.run(['tpm2_create',
                    '--quiet',
                    '--policy', os.path.join(workspace_dir, 'policy.digest'),
                    '--parent-context', os.path.join(workspace_dir, 'primary.context'),
                    '--sealing-input', '/secret.bin',
                    '--public', os.path.join(workspace_dir, 'object.public'),
                    '--private', os.path.join(workspace_dir, 'object.private')], check=True)
  subprocess.run(['tpm2_load',
                    '--quiet',
                    '--parent-context', os.path.join(workspace_dir, 'primary.context'),
                    '--public', os.path.join(workspace_dir, 'object.public'),
                    '--private', os.path.join(workspace_dir, 'object.private'),
                    '--key-context', os.path.join(workspace_dir, 'load.context')], check=True)
  subprocess.run(['tpm2_evictcontrol',
                    '--quiet',
                    '--object-context', os.path.join(workspace_dir, 'load.context'),
                    '--hierarchy', TPM_RH_OWNER,
                    tpm_address], check=True)

  if was_autorun:
    maybe_kill_windows_boot_manager()
    msg = ('!'*80) + '\n' + \
          'Adding blank password to partitions\n' + \
          'IMPORTANT: Reboot and run Setup TPM Auto-Decrypt to finish setup!\n' + \
          '           This OS will not be secure until you do!\n' + \
          ('!'*80) + '\n'
    print(msg)
    if shutil.which('xmessage') and shutil.which('nohup'):
      subprocess.Popen(['nohup', 'xmessage', msg], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    for partition in (root_path, home_partition, var_partition):
      if partition:
        subprocess.run(['cryptsetup', 'luksAddKey', partition, '--key-file', '/secret.bin'], input = BLANK_PASSWORD + b'\n', check = True)
  else:
    for partition in (root_path, home_partition, var_partition):
      if partition:
        print('Removing blank password from partition', partition)
        remove_blank_password(partition)

  if was_autorun:
    print('Updating mkinitcpio hooks')
    if USE_SYSTEMD_INIT:
      if not device_is_steamdeck() and REBOOT_TIMER_DURATION > 0:
        template = (UNSEAL_SCRIPT_TEMPLATE
                    .replace('$reboot_timer_code',
                              REBOOT_TIMER_SCRIPT_TEMPLATE)
                    .replace('$reboot_timer_duration',
                              str(REBOOT_TIMER_DURATION)))
      else:
        template = UNSEAL_SCRIPT_TEMPLATE.replace('$reboot_timer_code\n', '')
      ensure_file_has_desired_contents(UNSEAL_SCRIPT_PATH, template
                                        .replace('$tpm_address', tpm_address)
                                        .replace('$hash_algorithm',
                                                 hash_algorithm)
                                        .replace('$pcr_list', PCR_LIST),
                                        mode = stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    else:
      ensure_file_has_desired_contents(RUN_HOOK_PATH, RUN_HOOK_TEMPLATE
                                        .replace('$tpm_address', tpm_address)
                                        .replace('$hash_algorithm', hash_algorithm)
                                        .replace('$pcr_list', PCR_LIST))
    try:
      if USE_SYSTEMD_INIT:
        ensure_file_has_desired_contents(
          INSTALL_HOOK_PATH,
          SD_INSTALL_HOOK_TEMPLATE
            .replace('$UNSEAL_SCRIPT_PATH', UNSEAL_SCRIPT_PATH)
            .replace('$UNSEAL_SERVICE_PATH', UNSEAL_SERVICE_PATH),
        )
      else:
        ensure_file_has_desired_contents(
          INSTALL_HOOK_PATH,
          INSTALL_HOOK_TEMPLATE,
        )
    except FileExistsError:
      pass
    if USE_SYSTEMD_INIT:
      ensure_file_has_desired_contents(
        UNSEAL_SERVICE_PATH,
        UNSEAL_SERVICE_TEMPLATE.replace('$UNSEAL_SCRIPT_PATH', UNSEAL_SCRIPT_PATH),
      )
    targets = '\n'.join(('Target = '+i for i in PACMAN_PACKAGE_NAMES))
    ensure_file_has_desired_contents(
      PACMAN_BEFORE_HOOK_PATH,
      PACMAN_BEFORE_HOOK_TEMPLATE.replace('$TARGETS', targets),
    )
    script_cmd = [BIN_PATH, '--setup_auto_tpm_decrypt']
    script_cmd += ['--esp', esp_partition]
    if home_partition:
      script_cmd += ['--home', home_partition]
    if var_partition:
      script_cmd += ['--var', var_partition]
    if efi_bin_suffix:
      script_cmd += ['--suffix', efi_bin_suffix]
    if secure_boot_key:
      script_cmd += ['--key', secure_boot_key]
    if secure_boot_cert:
      script_cmd += ['--cert', secure_boot_cert]
    ensure_file_has_desired_contents(
      PACMAN_HOOK_PATH,
      PACMAN_HOOK_TEMPLATE
        .replace('$TARGETS', targets)
        .replace('$script_cmd', shlex.join(script_cmd)),
    )

    mkinitcpio_buf = []
    mkinitcpio_cfg_path = '/etc/mkinitcpio.conf'
    if not os.path.exists(mkinitcpio_cfg_path):
      mkinitcpio_cfg_path = '/etc/ostree-mkinitcpio.conf'
    if not os.path.exists(mkinitcpio_cfg_path):
      die('Unable to find mkinitcpio config')
    with open(mkinitcpio_cfg_path, 'r') as f:
      for line in map(str.strip, f):
        match = re.match(r'^HOOKS\s*=\s*(".+"|\(.+\))$', line)
        if match:
          device_manager = 'systemd' if USE_SYSTEMD_INIT else 'udev'
          encryption_hook = 'sd-encrypt' if USE_SYSTEMD_INIT else 'encrypt'
          hooks_to_remove = ('udev', 'encrypt') if USE_SYSTEMD_INIT else ('systemd', 'sd-encrypt')
          # root_fstype = get_partition_stats_via_blkid()[get_partition_for_mountpoint('/')]['TYPE']

          hooks = match.group(1)[1:-1].split()
          for hook in hooks_to_remove:
            if hook in hooks:
              hooks.remove(hook)
          if 'base' not in hooks:
            hooks.insert(0, 'base')
          if device_manager not in hooks:
            hooks.insert(hooks.index('base') + 1, device_manager)
          if 'autodetect' not in hooks:
            hooks.insert(hooks.index(device_manager) + 1, 'autodetect')
          if 'modconf' not in hooks:
            hooks.insert(hooks.index('autodetect') + 1, 'modconf')
          if 'block' not in hooks:
            hooks.insert(hooks.index('modconf') + 1, 'block')
          if encryption_hook not in hooks:
            hooks.insert(hooks.index('block') + 1, encryption_hook)
          if 'auto_tpm_encrypt' not in hooks:
            hooks.insert(hooks.index(encryption_hook), 'auto_tpm_encrypt')
          mkinitcpio_buf.append('HOOKS=(' + ' '.join(hooks) + ')')
        else:
          mkinitcpio_buf.append(line)

    tmp_mkinitcpio_cfg_path = os.path.join(workspace_dir, 'mkinitcpio.conf')
    with open(tmp_mkinitcpio_cfg_path, 'w') as f:
      f.write('\n'.join(mkinitcpio_buf))

    print('Ensuring sbctl post hook can be skipped')
    # HACK HACK HACK this will modify the post hook so it can be manually skipped
    #                this section should be updated if mkinitcpio ever adds a way
    #                to skip certain post hooks or if arch's sbctl updates to skip
    #                signing when keys don't exist in the default path
    sbctl_post_hook_path = '/usr/lib/initcpio/post/sbctl'
    sbctl_skip_var_name = 'SKIPSBCTLPOSTHOOK'
    sbctl_skip_code = 'if [ "x$SKIPSBCTLPOSTHOOK" != "x" ]; then exit 0; fi # added by auto_tpm_encrypt\n\n'
    try:
      with open(sbctl_post_hook_path, 'r') as f:
        sbctl_script = f.read()
      if sbctl_skip_var_name not in sbctl_script:
        if 'echo' not in sbctl_script:
          die('Unable to handle this version of the sbctl post hook. See if there is a newer version of auto_tpm_encrypt.')
        idx = sbctl_script.rfind('echo')
        with open(sbctl_post_hook_path+'.swap', 'w') as f:
          f.write(sbctl_script[:idx] + sbctl_skip_code + sbctl_script[idx:])
        os.rename(sbctl_post_hook_path+'.swap', sbctl_post_hook_path)
    except FileNotFoundError:
      pass

    print('Generating initramfs')
    tmp_initramfs = os.path.join(workspace_dir, 'initramfs.img')
    env = dict(os.environ)
    env[sbctl_skip_var_name] = '1'
    subprocess.run(['mkinitcpio',
                      '--config', tmp_mkinitcpio_cfg_path,
                      '--kernel', kernel_name,
                      '--generate', tmp_initramfs],
                      env = env,
                      check = True)

    print('Generating EFI bin')
    osrel_path = '/usr/lib/os-release'
    tmp_efi_bin = os.path.join(workspace_dir, 'boot.efi')
    if should_use_secure_boot_signing():
      tmp_signed_efi_bin = tmp_efi_bin
      tmp_efi_bin += '.unsigned'
    offset = max(map(lambda i: int(i[0], 16) + int(i[1], 16),
                     re.findall(r'\.[a-z]+\s+([a-f0-9]+)\s+([a-f0-9]+)',
                                subprocess.check_output(['objdump', '-h', EFI_STUB_PATH]).decode().lower())))
    private_headers_output = subprocess.check_output(['objdump', '-p', EFI_STUB_PATH]).decode()
    if not re.search(r'magic\s+[a-f0-9]+\s+\(pe', private_headers_output.lower()):
      die('EFI stub is not a PE binary')
    match = re.search(r'SectionAlignment\s+([a-f0-9]+)', private_headers_output)
    if not match:
      die('SectionAlignment not in EFI stub headers')
    align = int(match.group(1), 16)
    offset += align - (offset % align)
    osrel_offset = offset
    offset += os.path.getsize(osrel_path)
    offset += align - (offset % align)
    kernel_args_offset = offset
    offset += len(kernel_args)
    offset += align - (offset % align)
    kernel_offset = offset
    offset += os.path.getsize(kernel_bin)
    offset += align - (offset % align)
    initramfs_offset = offset
    subprocess.run(['objcopy',
                      '--add-section', '.osrel=' + osrel_path, '--change-section-vma', '.osrel=0x%X' % osrel_offset,
                      '--add-section', '.cmdline=' + kernel_args_path, '--change-section-vma', '.cmdline=0x%X' % kernel_args_offset,
                      '--add-section', '.linux=' + kernel_bin, '--change-section-vma', '.linux=0x%X' % kernel_offset,
                      '--add-section', '.initrd=' + tmp_initramfs, '--change-section-vma', '.initrd=0x%X' % initramfs_offset,
                      EFI_STUB_PATH,
                      tmp_efi_bin], check = True)

    if should_use_secure_boot_signing():
      print('Signing EFI bin')
      subprocess.run(['sbsign',
                       '--key', secure_boot_key,
                       '--cert', secure_boot_cert,
                       tmp_efi_bin,
                       '--output', tmp_signed_efi_bin])
      tmp_efi_bin = tmp_signed_efi_bin

    if home_partition or var_partition:
      if not USE_SYSTEMD_INIT:
        print('Updating crypttab')
        with open('/etc/crypttab.initramfs', 'a+') as f:
          f.seek(0)
          original_lines = [line.strip() for line in f]
          if len(original_lines) > 1 and original_lines[-1] == '':
            original_lines.pop()

          working_copy = list(filter(lambda line: not line.endswith(ADDDED_COMMENT), original_lines))
          if home_partition:
            working_copy.append('tpm_encrypted_home ' + home_partition + ' /secret.bin luks,initramfs,keyscript=decrypt_keyctl' + ADDDED_COMMENT)
          if var_partition:
            working_copy.append('tpm_encrypted_var ' + var_partition + ' /secret.bin luks,initramfs,keyscript=decrypt_keyctl' + ADDDED_COMMENT)

          if working_copy != original_lines:
            f.seek(0)
            f.write('\n'.join(working_copy) + '\n')
            f.truncate()
            print('Updated')
          else:
            print('No changes made, nothing to update')

      print('Updating fstab')
      with open('/etc/fstab', 'r+') as f:
        original_lines = [line.strip() for line in f]
        if len(original_lines) > 1 and original_lines[-1] == '':
          original_lines.pop()

        fstab_on_steamos = is_chroot_steamos()
        encrypted_uuids = {root_uuid}
        if home_partition:
          encrypted_uuids.add(blkid_stats[home_partition]['UUID'])
        if var_partition:
          encrypted_uuids.add(blkid_stats[var_partition]['UUID'])

        working_copy = []
        for line in original_lines:
          if line.endswith(ADDDED_COMMENT):
            pass
          elif fstab_on_steamos and line.startswith('/dev/disk/by-partsets/'):
            working_copy.append(REMOVED_COMMENT + line)
          elif line.startswith('UUID=') and line.split()[0][5:] in encrypted_uuids:
            working_copy.append(REMOVED_COMMENT + line)
          else:
            working_copy.append(line)

        if home_partition:
          working_copy.append('/dev/mapper/tpm_encrypted_home /home ext4 defaults,nofail 0 2' + ADDDED_COMMENT)
        if var_partition:
          working_copy.append('/dev/mapper/tpm_encrypted_var /var ext4 defaults 0 2' + ADDDED_COMMENT)

        if working_copy != original_lines:
          f.seek(0)
          f.write('\n'.join(working_copy) + '\n')
          f.truncate()
          print('Updated')
        else:
          print('No changes made, nothing to update')

    print('Mounting ESP partition')
    esp_mount_point = tempfile.mkdtemp(prefix='esp_')
    subprocess.run(['mount', esp_partition, esp_mount_point], check = True)

    print('Copying EFI bin to ESP partition')
    if is_chroot_steamos():
      boot_steamcl_path = os.path.join(esp_mount_point, 'efi/boot/bootx64.efi')
      boot_steamcl_backup_path = os.path.join(get_or_create_data_dir(), 'bootx64.original.efi')
      steamcl_path = os.path.join(esp_mount_point, 'efi/steamos/steamcl.efi')
      steamcl_backup_path = os.path.join(get_or_create_data_dir(), 'steamcl.original.efi')
      try:
        atomic_rename_without_overwriting(boot_steamcl_path, boot_steamcl_backup_path)
      except FileExistsError:
        os.remove(boot_steamcl_path)
      atomic_rename_without_overwriting(tmp_efi_bin, boot_steamcl_path)
      try:
        atomic_rename_without_overwriting(steamcl_path, steamcl_backup_path)
      except FileExistsError:
        try:
          os.remove(steamcl_path)
        except FileNotFoundError:
          pass
      except FileNotFoundError:
        pass
    else:
      boot_dir = os.path.join(esp_mount_point, 'EFI', 'Boot')
      efi_path = os.path.join(boot_dir, 'Auto_TPM_Encrypted_Boot' + (('_'+efi_bin_suffix) if efi_bin_suffix else '' ) + '.efi')
      os.makedirs(boot_dir, exist_ok = True)
      shutil.move(tmp_efi_bin, efi_path)
    subprocess.run(['umount', esp_mount_point], check = True)

    if DO_MASK_STEAMCL_SERVICE and is_chroot_steamos():
      print('Disabling SteamCL installer')
      try:
        os.symlink('/dev/null', STEAMCL_SERVICE_MASK_PATH)
      except FileExistsError:
        pass

def add_blank_password(partition=None, key_file=None):
  if not partition:
    print('Enter the partition to add the password to:')
    partition = input('> ')
    print('')

  if partition not in get_partitions():
    die('Partition not found')

  if get_partitions()[partition]['fstype'] not in SUPPORTED_ENCRYPTED_FILESYSTEMS:
    die('Partition not encrypted')

  if not key_file:
    print('Enter the path of the key file:')
    key_file = input('> ')
    print('')

  if not os.path.isfile(key_file):
    die('Key not found')

  maybe_kill_windows_boot_manager()

  print('Adding password')
  subprocess.run(['cryptsetup', 'luksAddKey', partition, '--key-file', key_file], input = BLANK_PASSWORD + b'\n', check = True)
  print('Done')

def has_blank_password(part_path):
  proc = subprocess.run(['cryptsetup', 'open', part_path, 'current_tpm_encrypted_vol'], input = BLANK_PASSWORD + b'\n')
  if proc.returncode in (SUCCESS, DEVICE_IN_USE):
    if proc.returncode == SUCCESS:
      subprocess.run(['cryptsetup', 'close', 'current_tpm_encrypted_vol'], check = True)
    return True
  elif proc.returncode != PASSPHRASE_NOT_FOUND:
    die(str(proc.returncode) + ': Unexpected result when checking for blank password on ' + part_path)
  return False

def ensure_booted_os_is_sealed():
  root_stats = get_partition_stats_for_mountpoint('/')
  if not root_stats:
    die('Could not get stats for root')

  root_path = root_stats['path']

  esp_partition, home_partition, var_partition = get_non_root_partitions_from_hook()

  existing_address = get_existing_tpm_address_from_hooks()
  if not existing_address:
    die('Unable to get sealing address from hooks')

  partitions_to_check = [('root', root_path), ('home', home_partition), ('var', var_partition)]
  partitions_with_blank_password = []

  for part_name, part_path in partitions_to_check:
    if part_path is not None:
      print('Ensuring blank password removed from ' + part_name + ' partition')
      if has_blank_password(part_path):
        partitions_with_blank_password.append(part_name)

  if len(partitions_with_blank_password) == 0:
    print('Success! A sealing address was found and none of the partitions still have a blank password.')
    return True
  else:
    maybe_kill_windows_boot_manager()
    print('Failure! At least one partition still has a blank password:', partitions_with_blank_password)
    return False

def ensure_no_os_are_unsealed():
  partitions_with_blank_password = []
  for part, part_info in get_partitions().items():
    if part_info['fstype'] in SUPPORTED_ENCRYPTED_FILESYSTEMS:
      print('Checking ' + part + '...')
      if has_blank_password(part):
        partitions_with_blank_password.append(part)
    else:
      print('Skipping ' + part + ', not encrypted')

  existing_address = get_existing_tpm_address_from_hooks()

  res = (len(partitions_with_blank_password) == 0)
  if res:
    print('Success! None of the encrypted partitions had a blank password.')
  else:
    maybe_kill_windows_boot_manager()
    print('Failure! At least one partition still has a blank password:', partitions_with_blank_password)

  if not existing_address:
    print('WARNING: A sealing address could not be found for the currently booted OS.')
    print('         If you did not expect this OS to be encrypted, you can safely')
    print('         ignore this warning. If not, please please ensure your key was ')
    print('         sealed correctly.')

  return res

def verify_esp_against_manifest():
  print_esp_partitions()
  print('Select the ESP to verify:')
  esp_partition = input('> ')

  print('Mounting ESP')
  esp_mount_point = tempfile.mkdtemp(prefix='esp_')
  subprocess.run(['mount', esp_partition, esp_mount_point], check = True)

  print('Verifying ESP against manifest')
  if esp_matches_manifest(esp_mount_point, ESP_MANIFEST_PATH):
    print('  ESP matches manifest. The ESP has not been modified!')
  else:
    print('  ESP does not match manifest. The ESP has been modified!')

  print('Unmounting ESP')
  subprocess.run(['umount', esp_mount_point], check = True)

  if USE_STEAMOS_SECOND_STAGE_ESP_MANIFEST:
    print('Verifying second stage manifests (if any exist)')
    second_stage_esps = guess_steamos_second_stage_efi_partitions_from_esp(esp_partition)
    for second_stage_esp in second_stage_esps:
      label = get_partitions()[second_stage_esp]['partlabel']
      manifest_path = STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_PREFIX + label + STEAMOS_SECOND_STAGE_ESP_MANIFEST_PATH_EXTENSION
      subprocess.run(['mount', esp_partition, esp_mount_point], check = True)
      if esp_matches_manifest(esp_mount_point, ESP_MANIFEST_PATH):
        print('  ' + label + ': ESP matches manifest. The ESP has not been modified!')
      else:
        print('  ' + label + ': ESP does not match manifest. The ESP has been modified!')
      subprocess.run(['umount', esp_mount_point], check = True)

  os.rmdir(esp_mount_point)

  print('Done')


def try_to_find_keyfile():
  import glob
  p = os.path.join(DATA_DIR, 'secret-backup.*.bin')
  try:
    return os.path.abspath(sorted(glob.iglob(p), key=os.path.getmtime)[-1])
  except IndexError:
    die('Unable to find the key file')

STEAMOS_UPDATE_WIZARD_INSTRUCTIONS = '''
 -= SteamOS Update Wizard =-

This wizard is designed to automate many of the tedious steps required
to decrypt and re-encrypt SteamOS in order to install updates. This
wizard will only work if you have already set up your Steam Deck per
the included guide with this script. This wizard only supports Steam
Decks running SteamOS with a standard partition layout and it may not
correctly detect which partitions to modify under other environments.
As such, for safety, the wizard will abort if it detects a non-standard
SteamOS install. If that happens, you will have to either switch back to
a stock SteamOS partition layout or use the other options in this
script to manually decrypt and re-encrypt SteamOS.

While this wizard is designed to walk you through the whole process,
it still (unfortunately) requires many steps:

1) Run this wizard under SteamOS. A blank password will be added to the
   recovery partition.

2) Run this wizard under the recovery partition. SteamOS will be decrypted.

3) Boot back into SteamOS and install the SteamOS update while in game mode

4) After installing the update, while still in SteamOS, switch to desktop mode,
   run this script and note which partitions SteamOS is using after the update.

5) Run the wizard under the recovery partition. SteamOS will be re-encrypted.

6) Boot SteamOS, run this option to seal SteamOS' key, reboot and make sure
   SteamOS auto unseals at boot.

7) Boot back into the recovery partition, run this option again to reseal the
   recovery partition key, reboot and ensure the recovery partition key auto
   unseals at boot.

The wizard will automatically detect which step you are on based on the current
state of your Steam Deck.
'''.lstrip()

def steamos_update_wizard():
  print('\n' + STEAMOS_UPDATE_WIZARD_INSTRUCTIONS)
  print('Performing sanity checks...')
  if not device_is_steamdeck():
    die('This device is not a Steam Deck')
  print('This device is a Steam Deck')

  nvme_partitions = dict(filter(lambda i: re.match(r'/dev/nvme\d+n\d+p\d+$', i[0]),
                                get_partitions().items()))
  print('Found {} NVMe partition(s)'.format(len(nvme_partitions)))
  if len(nvme_partitions) != 8:
    die('Expected 8 NVMe partitions')

  sd_partitions = dict(filter(lambda i: re.match(r'/dev/mmcblk\d+p\d+$', i[0]),
                              get_partitions().items()))
  print('Found {} SD card partition(s)'.format(len(sd_partitions)))

  encrypted_sd_partitions = dict(filter(lambda i: i[1]['fstype'] in SUPPORTED_ENCRYPTED_FILESYSTEMS,
                                        sd_partitions.items()))
  print('Found {} encrypted SD card partition(s)'.format(len(encrypted_sd_partitions)))
  if len(encrypted_sd_partitions) != 1:
    die('Expected 1 encrypted SD card partition')

  esp_partitions = get_esp_partitions()
  print('Found {} ESP partition(s)'.format(len(esp_partitions)))
  if len(esp_partitions) != 2:
    die('Expected 2 ESP partitions')

  nvme_esp_partitions = {i:esp_partitions[i] for i in
                         set(esp_partitions.keys()).intersection(set(nvme_partitions.keys()))}
  print('Found {} NVMe ESP partition(s)'.format(len(nvme_esp_partitions)))
  if len(nvme_esp_partitions) != 1:
    die('Expected 1 NVMe ESP partition')
  nvme_esp_partition = list(nvme_esp_partitions.keys())[0]
  print('NVMe ESP Partition: {}'.format(nvme_esp_partition))

  sd_esp_partitions = {i:esp_partitions[i] for i in
                       set(esp_partitions.keys()).intersection(set(sd_partitions.keys()))}
  print('Found {} SD ESP partition(s)'.format(len(sd_esp_partitions)))
  if len(sd_esp_partitions) != 1:
    die('Expected 1 SD ESP partition')

  VALID_ENCRYPTED_STEAMOS_PARTITIONS = (
    ['/dev/nvme0n1p4', '/dev/nvme0n1p6', '/dev/nvme0n1p8'],
    ['/dev/nvme0n1p5', '/dev/nvme0n1p7', '/dev/nvme0n1p8'],
  )
  VALID_UNENCRYPTED_STEAMOS_PARTITIONS = ([],)
  VALID_ENCRYPTED_NVME_PARTITIONS = (
    VALID_ENCRYPTED_STEAMOS_PARTITIONS + VALID_UNENCRYPTED_STEAMOS_PARTITIONS
  )
  encrypted_nvme_partitions = dict(filter(lambda i: i[1]['fstype'] in SUPPORTED_ENCRYPTED_FILESYSTEMS,
                                          nvme_partitions.items()))
  sorted_encrypted_nvme_partitions = sorted(encrypted_nvme_partitions.keys())
  print('Found the following encrypted NVMe partition(s): {}'.format(sorted_encrypted_nvme_partitions))
  if sorted_encrypted_nvme_partitions not in VALID_ENCRYPTED_NVME_PARTITIONS:
    die('The NVMe partitions that were encrypted were not the ones which were expected')

  recovery_partition = list(encrypted_sd_partitions.keys())[0]
  print('Detected recovery partition as {}'.format(recovery_partition))
  recovery_partition_has_blank_password = has_blank_password(recovery_partition)
  print('Recovery partition has blank password: {}'.format(recovery_partition_has_blank_password))

  print('')

  if (sorted_encrypted_nvme_partitions in VALID_ENCRYPTED_STEAMOS_PARTITIONS and
      not recovery_partition_has_blank_password):
    print('Based on your current environment, you seem to be on step 1.')
    print('Continue to add a blank password to the recovery partition.')
    if input('(continue? y/n) ') != 'y':
      die('user chose not to continue')
    add_blank_password(partition = recovery_partition, key_file = try_to_find_keyfile())
  elif sorted_encrypted_nvme_partitions in VALID_ENCRYPTED_STEAMOS_PARTITIONS:
    if not is_steamos():
      print('Based on your current environment, you seem to be on either step 2 or 7.')
      print('Please enter the number of the step you are on (2 or 7) or enter anything')
      print('else to quit.')
      i = input('(step?) ')
      if i not in ('2','7'):
        die('user chose to quit')
      if i == '2':
        print('Your SteamOS partitions will be decrypted.')
        if input('(continue? y/n) ') != 'y':
          die('user chose not to continue')
        root, var, home = sorted(encrypted_nvme_partitions.keys())
        decrypt(root, home, var, nvme_esp_partition, key_file = try_to_find_keyfile())
      elif i == '7':
        print('Your recovery partition\'s key will be sealed and the blank')
        print('password will be removed.')
        if input('(continue? y/n) ') != 'y':
          die('user chose not to continue')
        setup_auto_tpm_decrypt()
        print('Done!')
    else:
      print('Based on your current environment, you seem to be on step 6.')
      print('If you continue, your SteamOS partitions\' key will be sealed')
      print('and the blank password will be removed.')
      if input('(continue? y/n) ') != 'y':
        die('user chose not to continue')
      setup_auto_tpm_decrypt()
      print('Done!')
  elif (sorted_encrypted_nvme_partitions in VALID_UNENCRYPTED_STEAMOS_PARTITIONS and
        recovery_partition_has_blank_password):
    print('Based on your current environment, you seem to be on step 5.')
    if is_steamos():
      die('Boot into the recovery partition for step 5')
    print('Continue to re-encrypt SteamOS')
    if input('(continue? y/n) ') != 'y':
      die('user chose not to continue')
    print('Per step 4, which partitions is SteamOS using?')
    print('Enter the number of your selection or enter anything else to quit.')
    for idx, opt in enumerate(VALID_ENCRYPTED_STEAMOS_PARTITIONS):
      print('  {0}) {1}'.format(idx+1, ' '.join(opt)))
    print('')
    i = input('(partitions?) ')
    if i not in [str(i+1) for i in range(len(VALID_ENCRYPTED_STEAMOS_PARTITIONS))]:
      die('user chose to quit')
    root, var, home = VALID_ENCRYPTED_STEAMOS_PARTITIONS[int(i)-1]
    encrypt(root, home, var, nvme_esp_partition)
  elif sorted_encrypted_nvme_partitions in VALID_UNENCRYPTED_STEAMOS_PARTITIONS:
    print('It looks like your SteamOS partitions are decrypted but your')
    print('recovery partition does not have a blank password. If you are')
    print('following the steps above, this should not be possible. Please')
    print('carefully reread the steps.')
    print('')
    print('To get you back on track, a blank password can be added to the')
    print('recovery partition. From there, you can follow steps 3, 4 or 5')
    print('depending on where you were when you got this message.')
    print('')
    if input('(continue? y/n) ') != 'y':
      die('user chose not to continue')
    add_blank_password(partition = recovery_partition, key_file = try_to_find_keyfile())
  else:
    die('Unexpected state. This should never happen.')


def menu():
  print('Do not use this script without first reading the guide.')
  print('Verify the information above is accurate then select an option.')
  print('If it is not accurate, select Quit!')
  print('')
  print('1) Encrypt/Decrypt an unbooted partition')
  print('2) Setup TPM auto-decrypt for the booted OS')
  print('3) Add blank password to unbooted partition')
  print('4) Verify booted OS is sealed')
  print('5) Verify no OS are unsealed')
  print('6) Verify ESP against manifest')
  print('7) SteamOS Update Wizard')
  print('Q) Quit')
  print('')
  inp = input('> ')
  if inp == '1':
    encrypt_or_decrypt()
  elif inp == '2':
    setup_auto_tpm_decrypt()
    print('Done!')
  elif inp == '3':
    add_blank_password()
  elif inp == '4':
    ensure_booted_os_is_sealed()
  elif inp == '5':
    ensure_no_os_are_unsealed()
  elif inp == '6':
    verify_esp_against_manifest()
  elif inp == '7':
    steamos_update_wizard()
  elif inp.lower() == 'q':
    return
  else:
    die('Invalid input')

def main():
  if '--setup_auto_tpm_decrypt' in sys.argv:
    return setup_auto_tpm_decrypt()

  print_sys_info_and_do_sanity_checks()
  if '--ensure_booted_os_is_sealed' in sys.argv:
    sys.exit(0 if ensure_booted_os_is_sealed() else 1)
  elif '--ensure_no_os_are_unsealed' in sys.argv:
    sys.exit(0 if ensure_no_os_are_unsealed() else 1)
  else:
    menu()

if __name__ == '__main__':
  main()
