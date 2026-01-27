import sys, os, shutil, subprocess, json, re, textwrap, io, tempfile, time
sys.dont_write_bytecode = True
import pivotzoneutils, pacman_helper

def logf(*msg):
  logstr = ' '.join(map(str, msg)) + '\n'
  with open('/mypivotzone_logs.txt', 'a') as f:
    f.write(logstr)
  if os.path.ismount('/run/PivotZone/backingroot'):
    with open('/run/PivotZone/backingroot/mypivotzone_logs.txt', 'a') as f:
      f.write(logstr)
  for tty in ('/dev/tty1', '/dev/ttyS0'):
    try:
      with open(tty, 'w') as f:
        f.write(logstr)
    except OSError:
      pass

coordinator = pivotzoneutils.PivotZoneCoordinator(size = '10G', log_func = logf)

coordinator.restart_service('NetworkManager.service')
coordinator.restart_service('wpa_supplicant.service')

core_paths = {
  '/sbin/ldconfig',
  '/etc/passwd*',
  '/etc/shadow*',
  '/etc/group',
  '/etc/shells',
  '/etc/environment',
  '/etc/resolv.conf',
  '/etc/mtab',
  '/etc/ld.so.conf**',
  '/usr/lib/ld.so.conf**',
  '/lib64/ld-linux-x86-64.so*',
  '/usr/lib/libc.so*',
  '/usr/lib/libgcc_s.so*',
  '/usr/lib/libm.so*',
  '/usr/lib/libncursesw.so*',
  '/usr/lib/libreadline.so*',
  '/usr/lib/libresolv.so*',
  '/usr/lib/libcrypt.so*',
  '/usr/lib/libgcrypt.so*',
  '/usr/lib/liblz4.so*',
  '/usr/lib/liblzo2.so*',
  '/usr/lib/liblzma.so*',
  '/usr/lib/libzstd.so*',
  '/usr/lib/libgpg-error.so*',
  '/bin',
  '/usr/sbin',
}

runuser_paths = {
  '/usr/bin/runuser',
  '/usr/lib/libpam.so*',
  '/usr/lib/libpamc.so*',
  '/usr/lib/libpam_misc.so*',
  '/usr/lib/libaudit.so*',
  '/usr/lib/libcap-ng.so*',
}

fuser_paths = {
  '/usr/bin/fuser',
  '/usr/bin/lsof',
  '/usr/lib/libtirpc.so*',
  '/usr/lib/libgssapi_krb5.so*',
  '/usr/lib/libkrb5.so*',
  '/usr/lib/libk5crypto.so*',
  '/usr/lib/libcom_err.so*',
  '/usr/lib/libkrb5support.so*',
  '/usr/lib/libkeyutils.so*',
}

systemd_paths = {
  '/etc/systemd/**',
  '/usr/bin/systemctl',
  '/usr/bin/loginctl',
  '/usr/bin/systemd-nspawn',
  '/usr/lib/systemd/**',
  '/usr/lib/libacl.so*',
  '/usr/lib/libkmod.so*',
  '/usr/lib/libmount.so*',
  '/usr/lib/libseccomp.so*',
}

mount_paths = {
  '/usr/bin/mount',
  '/usr/bin/umount',
}

bash_paths = {
  '/usr/bin/bash',
  '/usr/bin/sh',
}

busybox_paths = {'/usr/bin/busybox'}

luks_paths = {
  '/secret.bin',
  '/usr/bin/cryptsetup',
  '/usr/lib/libcryptsetup.so*',
  '/usr/lib/libpopt.so*',
  '/usr/lib/libuuid.so*',
  '/usr/lib/libblkid.so*',
  '/usr/lib/libdevmapper.so*',
  '/usr/lib/libcrypto.so*',
  '/usr/lib/libargon2.so*',
  '/usr/lib/libjson-c.so*',
  '/usr/lib/libudev.so*',
}

tmux_paths = {
  '/etc/locale.conf',
  '/usr/lib/locale/**',
  '/usr/lib/libsystemd.so*',
  '/usr/lib/libutempter.so*',
  '/usr/lib/libevent_core*',
  '/usr/lib/libcap.so*',
  '/usr/bin/tmux',
  '/usr/share/terminfo/**',
}

nano_paths = {
  '/usr/bin/nano',
  '/usr/bin/rnano',
  '/etc/nanorc',
  '/usr/share/nano/**',
  '/usr/lib/libmagic.so*',
  '/usr/lib/libz.so*',
  '/usr/lib/libbz2.so*',
}

python_paths = {
  '/usr/bin/python*',
  '/usr/lib/python*/**',
  '/usr/lib/libpython*',
  '/usr/bin/ldd',
  __file__,
  pivotzoneutils.__file__,
}

misc_paths = {
  '/usr/bin/login',
  '/etc/pam.d/**',
  '/etc/login.defs',
  '/var/spool/mail/**',
  '/usr/local/sbin/**',
  '/usr/local/bin/**',
  '/etc/securetty',
  '/etc/security/**',
  '/usr/lib/security/**',
  '/usr/bin/passwd',
  '/usr/lib/libsubid.so*',
  '/root',
  '/usr/bin/fail*',
  '/usr/bin/pwc*',
  '/usr/bin/nologin',
  '/usr/lib/sysusers.d/**',
  '/usr/bin/agetty',
  '/usr/bin/pam*',

  '/usr/bin/mkhomedir_helper',
  '/usr/bin/pwhistory_helper',
  '/usr/bin/unix_chkpwd',
  '/usr/bin/unix_update',

  '/usr/lib/libsmartcols.so*',
  '/usr/bin/zramctl',

  '/usr/bin/dmsetup',
  '/usr/bin/lsns',
  '/usr/bin/lvchange',
  '/usr/bin/lvm',
  '/usr/lib/libdevmapper-event.so*',
  '/usr/lib/libaio.so*',

  '/usr/bin/udisksctl',
  '/usr/lib/libpolkit*',
  '/usr/lib/libudisks*',
  '/usr/lib/libgio*',
  '/usr/lib/libgobject*',
  '/usr/lib/libglib*',
  '/usr/lib/libgmodule*',
  '/usr/lib/libpcre*',
  '/usr/lib/libffi*',
  '/usr/lib/udisks2/**',
  '/usr/lib/libgudev*',
  '/usr/lib/libblockdev*',
  '/usr/lib/libbd_utils*',
  '/usr/lib/libatasmart*',

  '/usr/bin/journalctl',
  '/usr/bin/dmesg',
  '/usr/bin/less',
  '/usr/bin/which',

  '/usr/bin/dbus*',
  '/usr/lib/libexpat*',

  '/usr/bin/btrfs*',

  '/usr/bin/pivot_root',

  os.path.join(os.path.dirname(__file__), 'check_why_busy.py'),
  os.path.join(os.path.dirname(__file__), 'pacman_helper.py'),

  '/usr/bin/sleep',
  '/usr/bin/chvt',

  # '/etc/pacman.conf',
  # '/usr/bin/pacman*',
  # '/usr/share/pacman/**',
  # '/usr/share/makepkg/**',
  # '/usr/bin/parseopts',
  # '/usr/bin/gpg*',
  # '/usr/bin/vercmp',
  # '/etc/pacman.d/**',
  # '/usr/lib/libnpth.so*',
  # '/usr/lib/libsqlite3.so*',
  # '/usr/lib/libalpm.so*',
  # '/usr/lib/libarchive.so*',
  # '/usr/lib/libcurl.so*',
  # '/usr/lib/libgpgme.so*',
  # '/usr/lib/libexpat.so*',
  # '/usr/lib/libbz2.so*',
  # '/usr/lib/libnghttp*',
  # '/usr/lib/libnghttp*',
  # '/usr/lib/libidn2.so*',
  # '/usr/lib/libssh2.so*',
  # '/usr/lib/libpsl.so*',
  # '/usr/lib/libssl.so*',
  # '/usr/lib/libssl.so*',
  # '/usr/lib/libbrotlidec.so*',
  # '/usr/lib/libassuan.so*',
  # '/usr/lib/libunistring.so*',
  # '/usr/lib/libbrotlicommon.so*',
  # '/var/lib/pacman/**',
  # '/var/cache/pacman/**',
  # '/etc/ssl/**',
  # '/usr/lib/engines-3/**',
  # '/usr/lib/ossl-modules/**',
}

non_package_paths = {
  os.path.dirname(__file__)+'/**',
  '/secret.bin',
  '/etc/ca-certificates/extracted/tls-ca-bundle.pem'
}

paths_to_install_when_entering_zone = {
  *core_paths, *bash_paths, *runuser_paths, *fuser_paths, *systemd_paths,
  *mount_paths, *busybox_paths, *luks_paths, *tmux_paths, *python_paths,
  *nano_paths, *misc_paths,
}

packages_to_include_when_entering_zone = [
  'base', 'cryptsetup', 'tmux', 'busybox', 'micro', 'less', 'which',
  'btrfs-progs', 'python', 'util-linux', 'fluxbox', 'networkmanager', 'linux',
  'man', 'bsd-games', 'libvirt', 'kmod', 'linux-firmware',
]

excluded_paths = {'*.pyc', '**/site-packages/**', '**/__pycache__', '/proc/**',
                  '/run/**', '/dev/**', '/sys/**', '/tmp/**'}

js_path = '/mypivotzone_created_path.json'

def _arm_common(get_paths_func):
  if os.path.exists(coordinator.make_zone_path(js_path)):
    print('Already armed!')
    return

  print('Arming zone...')
  start = time.time()

  paths_to_install = get_paths_func()

  created = coordinator.copy_into_zone(paths_to_install,
                                         excluded_paths)

  with open(coordinator.make_zone_path(js_path), 'x') as f:
    json.dump(list(created), f)

  ttys = (f'/etc/systemd/system/getty@{i}.service.d/autologin.conf'
            for i in ('tty3', 'ttyS0'))

  for tty in ttys:
    os.makedirs(os.path.dirname(coordinator.make_zone_path(tty)))
    with open(coordinator.make_zone_path(tty), 'x') as f:
      f.write(textwrap.dedent('''
          [Service]
          ExecStart=
          ExecStart=-/sbin/agetty -o '-p -f -- \\u' --noclear --autologin root %I $TERM
        '''))

  pacman_helper.disable_pacman_systemd_units_within_zone(coordinator)

  print('Arming took', (time.time()-start), 'second(s)')


def arm_using_a_minimal_set_of_paths():
  _arm_common(lambda: paths_to_install_when_entering_zone)


def arm_using_package_manager():
  def get_paths():
    paths = set(non_package_paths)
    for package in packages_to_include_when_entering_zone:
      paths.update(pacman_helper.get_files_from_package(package))
    return paths
  _arm_common(get_paths)


def disarm():
  try:
    with open(coordinator.make_zone_path(js_path), 'r') as f:
        created = json.load(f) + [f.name]
  except FileNotFoundError:
    print('Already disarmed!')
    return
  for i in created:
    if os.path.islink(i) or os.path.isfile(i):
      os.remove(i)
    elif os.path.isdir(i):
      shutil.rmtree(i)


def boot_flow():
  os.chdir(os.path.dirname(__file__))

  if not coordinator.is_in_zone():
    arm_using_package_manager()
    # arm_using_a_minimal_set_of_paths()
    subprocess.run(('umount', '/efi'))
    subprocess.check_call((sys.executable, __file__, 'bg',
                           sys.executable, __file__, 'boot'))
    return

  try:
    subprocess.check_call(('systemctl', 'stop', 'display-manager.service'))

    # time.sleep(10)
    subprocess.check_call(('chvt', '3'))
    subprocess.check_call(('chvt', '1'))

    # time.sleep(15) # TODO poll display manager

    for i in range(4, 0, -1):
      subprocess.run(('systemctl', 'start', f'getty@tty{i}.service'))

    tmux_waiter = subprocess.Popen(('sleep', 'infinity'))

    # Set tmux to auto start in the PivotZone
    with open('/root/.bash_profile', 'a') as f:
      f.write(textwrap.dedent(f'''
        if [ "x$TMUX" == "x" ]; then
          tmux new -A -s PivotZone
          kill -INT {tmux_waiter.pid}
        fi
      '''))

    o = subprocess.check_output(('systemctl', 'status')).decode()
    logf('SYSTEMCTL_STATUS_PRE_ENTER:\n' + o + '\n\n')

    # subprocess.check_call(('chvt', '2'))
    # time.sleep(3) # TODO
    # subprocess.run(('systemctl', 'restart', f'getty@tty1.service'))
    # time.sleep(3) # TODO
    # subprocess.check_call(('chvt', '1'))

    # Enter the PivotZone
    coordinator.enter()

    # Boot the VM

    # Read the root drive's uuid from kernel args and store it for later
    with open('/proc/cmdline', 'r') as f:
      cmdline = f.read()
    root_device = '/dev/disk/by-uuid/' + [i[13:].split('=')[0] for i in
                  filter(lambda i: i.startswith('rd.luks.name='),
                         cmdline.split())][0]

    # Change the VT in case were using the wrong one
    subprocess.check_call(('chvt', '3'))

    # coordinator.wait_for_nbd_and_tell_daemon()

    # Wait for VM shutdown
    tmux_waiter.wait()

    # Mount and decrypt the root drive
    subprocess.check_call(('cryptsetup', 'open',
                           root_device,
                           'tpm_encrypted_root',
                           '--key-file', '/secret.bin'))

    # Exit the PivotZone
    coordinator.exit()

    # Use a temporary bind mount to autologin just for this login
    cpath = '/etc/sddm.conf.d/kde_settings.conf'
    with open(cpath, 'r') as f:
      conf = f.read()
    for k,v in (('Relogin','true'),('Session','plasma'),('User','Liz')):  # TODO: auto get username
      conf = re.sub(k+'=.*', k+'='+v, conf)
    tf = tempfile.NamedTemporaryFile(mode = 'w', prefix = 'sddm_conf_')
    tf.write(conf)
    tf.flush()
    os.chmod(tf.fileno(), os.stat(cpath).st_mode)
    subprocess.check_call(('mount', '--bind', tf.name, cpath))
    subprocess.check_call(('systemctl', 'start', 'display-manager.service'))

    # Remove everything that was copied into the PivotZone during arming
    disarm()

    time.sleep(15) # NB: assumes logging in won't take longer than this time
    subprocess.check_call(('umount', cpath))
  except Exception as exc:
    import traceback
    logf(' --- Exception --- \n' + str(exc) + '\n' +
         (''.join(traceback.format_exception(exc))) + '\n\n')


if __name__ == '__main__' and len(sys.argv) > 1:
  if sys.argv[1] == 'build':
    coordinator.build()
  elif sys.argv[1] == 'destroy':
    coordinator.destroy()
  elif sys.argv[1] == 'exec':
    coordinator.exec(sys.argv[2] , sys.argv[2:])
  elif sys.argv[1] == 'bg':  # TODO make a version of this which sets PATH et al to use nvram so it can be used with an unarmed zone
    subprocess.check_call(['systemd-run',
                           sys.executable, __file__, 'exec'] + sys.argv[2:])
  elif sys.argv[1] == 'tmux':
    arm_using_package_manager()
    subprocess.check_call(('systemd-run', '-r',
                           sys.executable, '-c',
                           'import subprocess,pty;p=pty.openpty();print(subprocess.run(("tmux", "new", "-v", "-Aszone"), stdin=p[1], stdout=p[0], stderr=p[0], cwd="/tmp"))'))
    # subprocess.check_call(('systemd-run',
    #                        sys.executable, '-c',
    #                        'import subprocess,pty;p=pty.openpty();subprocess.run(("tmux", "new", "-Aszone"), stdin=p[0], stdout=p[1], stderr=p[1])'))
    # coordinator.exec('bash', ['bash'])
    # coordinator.exec('tmux', ('tmux', 'a', '-tzone'))
    # tmux a -t zone
  elif sys.argv[1] == 'arm':
    arm_using_package_manager()
  elif sys.argv[1] == 'disarm':
    disarm()
  elif sys.argv[1] == 'barm':
    coordinator.build()
    arm_using_package_manager()
  elif sys.argv[1] == 'boot':
    boot_flow()
  elif sys.argv[1] == 'iiz':
    print(coordinator.is_in_zone())
  elif sys.argv[1] == 'dbg':
    breakpoint()
  elif sys.argv[1] == 'dbg1':
    subprocess.check_call(['systemd-run', sys.executable, __file__, 'dbg2'])
  elif sys.argv[1] == 'dbg2':
    subprocess.check_call(('systemctl', 'stop', 'display-manager.service'))
    for _ in range(5):
      time.sleep(3)
      subprocess.check_call(('systemctl', 'restart', 'getty@tty1.service'))
