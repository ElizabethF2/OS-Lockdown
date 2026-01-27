#!/usr/bin/env python3

import sys, os, pwd, subprocess, json, shutil, re

def try_reboot_kde():
  if os.environ.get('XDG_CURRENT_DESKTOP') != 'KDE':
    return False
  addr = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
  if not addr:
    addr = os.environ.get('SUDO_DBUS_SESSION_BUS_ADDRESS')
  if not addr:
    for arg in sys.argv:
      if arg.startswith('DBUS_SESSION_BUS_ADDRESS='):
        addr = arg[25:]
  if not addr:
    uid = os.environ.get('SUDO_UID')
    if uid:
      path = os.path.join('/run', 'user', uid, 'bus')
      if os.path.exists(path):
        addr = 'unix:path=' + path
  if not addr:
    return False
  qdbus = shutil.which('qdbus') or \
          shutil.which('qdbus6') or \
          shutil.which('qdbus5')
  if not qdbus:
    return False
  if os.getuid() != 0:
    subprocess.run((qdbus,
                    'org.kde.Shutdown',
                    '/Shutdown',
                    'org.kde.Shutdown.logoutAndReboot'))
    return True
  user = os.environ.get('SUDO_USER')
  if not user:
    return False
  sudo = shutil.which('sudo')
  if not sudo:
    return False
  subprocess.run((sudo,
                  'DBUS_SESSION_BUS_ADDRESS='+addr,
                  '-u', user,
                  qdbus,
                  'org.kde.Shutdown',
                  '/Shutdown',
                  'org.kde.Shutdown.logoutAndReboot'))
  return True

print('Load shell list...')
with open('/etc/shells', 'r') as f:
  valid_shells = set(filter(lambda i: i and i[0] != '#',
                            map(str.strip, f.readlines())))

# Check for any syncs that are due
users_with_sync_due = []
if shutil.which('prbsync'):
  if '--nosync' in sys.argv:
    print('WARNING: skipping file synchronization')
  else:
    print('Checking synced files...')
    for user in pwd.getpwall():
      if user.pw_shell not in valid_shells:
        continue
      p = subprocess.run(
        ('runuser', '-u'+user.pw_name, '--', 'prbsync', 'json_query'),
        stdout = subprocess.PIPE, stderr = subprocess.DEVNULL,
        shell = False, check = False)
      js = json.loads(p.stdout)
      if js['sync_due']:
        print(user.pw_name + ' has a sync due!')
        users_with_sync_due.append(user.pw_name)
      if any(('auto_sync_filter' in p for p in js['config']['syncable_paths'].values())):
        subprocess.run(
          ('runuser', '-u'+user.pw_name, '--', 'prbsync', 'auto_sync'),
          shell = False, check = True)
        p = subprocess.run(
          ('runuser', '-u'+user.pw_name, '--', 'prbsync', 'json_query'),
          stdout = subprocess.PIPE, stderr = subprocess.DEVNULL,
          shell = False, check = False)
        if json.loads(p.stdout)['sync_due'] and user.pw_name not in users_with_sync_due:
          users_with_sync_due.append(user.pw_name)

if len(users_with_sync_due) > 0:
  print('Some users have syncs due: ' + ', '.join(users_with_sync_due))
  print('Sync everything before switching OS')
  sys.exit(1)

print('Verifying all encrypted OS are sealed before booting Windows...')

auto_tpm_encrypt = shutil.which('auto_tpm_encrypt')
if not auto_tpm_encrypt:
  auto_tpm_encrypt = os.path.join(os.path.dirname(__file__),
                                  'auto_tpm_encrypt')
ret = subprocess.check_call((auto_tpm_encrypt, '--ensure_no_os_are_unsealed'),
                            env = os.environ | {'IGNORE_IF_ON_BATTERY': '1'})

if ret == 0:
  print('Booting Windows...')
  out = subprocess.check_output('efibootmgr')
  bootnum = None
  for num, name in re.findall(r'Boot(\d{4})\*\s*([^\t]+)\t', out.decode()):
    if name == 'Windows':
      bootnum = num
  if not bootnum:
    raise FileNotFoundError('Unable to find bootnum for Windows')
  subprocess.run(('efibootmgr', '--bootnext', bootnum))
  if not try_reboot_kde():
    subprocess.run(('reboot',))
