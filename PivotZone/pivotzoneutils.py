import sys, os, glob, fnmatch, stat, subprocess, shutil, shlex, json, time
import signal

_RUN_DIR = '/run/PivotZone'
_ZONEROOT = os.path.join(_RUN_DIR, 'zoneroot')
_BACKINGROOT = os.path.join(_RUN_DIR, 'backingroot')
_RAMDEV = os.path.join(_RUN_DIR, 'ramdev')
_ROOTDEV = os.path.join(_RUN_DIR, 'rootdev')
_NVREADYFLAG = os.path.join(_RUN_DIR, 'nvready')
_PFSHOLDER = os.path.join(_RUN_DIR, 'pfsholder')
_ZRUNHOLDERNAME = 'PivotZone_zone_run_holder'
_PFS = ('dev', 'proc', 'sys', 'run', 'tmp')
_SHARED_PFS = ('run',)
_EXCLUDED_PFS = ('/run/user', _RUN_DIR)
_RESERVED_PATHS = {'nvroot', *_PFS, _ZRUNHOLDERNAME}
_DEFAULT_LOG_FUNC = lambda *msg: None

_ONLY_OWNER_CAN_WRITE = 0o755
_ONLY_OWNER_CAN_ACCESS = 0o700


RETRY_COUNT = 50
RETRY_DELAY = 0.5


def _get_exes():
  exes = []
  for pid in filter(str.isdigit, os.listdir('/proc')):
    try:
      exes.append((int(pid), os.readlink(f'/proc/{pid}/exe')))
    except FileNotFoundError:
      continue
  return exes


class SystemdServiceManager(object):
  def __init__(self, log_func = _DEFAULT_LOG_FUNC):
    self.stuborn_services = ('/systemd-userdbd', '/systemd-userwork',
                             '/systemd-logind', '/systemd-networkd',
                             '/systemd-udevd', '/systemd-journald') # TODO nicer way to restart these but still drop refs?
    self.needs_run_directory = True  # TODO use or remove this
    self.log = log_func

  def get_logged_in_users(self):
    for _ in range(RETRY_COUNT):
      try:
        return tuple(
            i['user'] for i in filter(lambda i: i['uid'] != 0,
              json.loads(subprocess.check_output(
                ('loginctl', 'list-sessions', '-j')).decode())))
      except subprocess.CalledProcessError as exc:
        time.sleep(RETRY_DELAY)
        stored_exc = exc
    raise stored_exc

  def get_active_units(self, user = None):
    cmd = ['systemctl', 'list-units', '--output=json']
    if user is not None:
      cmd += ['-M', user+'@', '--user']
    js = json.loads(subprocess.check_output(cmd).decode())
    ret = {unit['unit']: (unit['sub'] in ('running', 'listening'))
             for unit in js}
    return {unit['unit']: (unit['sub'] in ('running', 'listening'))
            for unit in js}

  def stop_service(self, service_name, user = None):
    if user is None:
      self.log(subprocess.run(('systemctl', 'stop', service_name),
                                   capture_output = True))
    else:
      self.log(subprocess.run(('systemctl', '-M', user+'@',
                      '--user', 'stop', service_name),
                      capture_output = True))

  def restart_service(self, service_name, user = None):
    if user is None:
      self.log(subprocess.run(('systemctl', 'restart', service_name),
                                   capture_output=True))
    else:
      self.log(subprocess.run(('systemctl', '-M', user+'@',
                      '--user', 'restart', service_name),
                      capture_output = True))

  def reexec(self):
    subprocess.check_call(('systemctl', 'daemon-reexec'))
    # os.kill(1, signal.SIGTERM)

  def force_restart_stuborn_services(self):
    for pid, exe in _get_exes():
      if any(exe.endswith(i) for i in self.stuborn_services):
        sig = signal.SIGTERM
        self.log(f'Killing stuborn service PID: {pid} EXE: {exe} SIG: {sig}')
        os.kill(pid, sig)


class SysVServiceManager(object):
  def __init__(self, initd = None):
    self.initd = '/etc/init.d' if initd is None else initd
    self.needs_run_directory = True

  def get_logged_in_users(self):
    return tuple()

  def get_active_units(self, user = None):
    units = {}
    services = set(os.listdir(self.initd))
    rc_status = shutil.which('rc-status')
    if rc_status:
      o = subprocess.check_output((rc_status)).decode()
      for service, *status in map(str.split, o.splitlines()):
        if service in services:
          units[service] = ('started' in map(str.lower, status))
    else:
      for service in services:
        p = subprocess.run((os.path.join(self.initd, service), 'status'),
                           capture_output = True)
        active = (p.returncode == 0)
        units[service] = active
    return units

  def stop_service(self, service_name, user = None):
    subprocess.run((os.path.join(self.initd, service_name), 'stop'))

  def restart_service(self, service_name, user = None):
    subprocess.run((os.path.join(self.initd, service_name), 'restart'))

  def reexec(self):
    subprocess.run(('telinit', 'U'))

  def force_restart_stuborn_services(self):
    pass


class PivotZoneCoordinator(object):
  def __init__(
    self,
    algorithm = 'zstd',
    size = '2G',
    pivotzoned = 'pivotzoned',
    service_manager = None,
    log_func = _DEFAULT_LOG_FUNC):

    self.algorithm = algorithm
    self.size = str(size)
    self.pivotzoned = pivotzoned
    self.service_manager = (service_manager if service_manager is not None
                              else SystemdServiceManager(log_func = log_func))
    self.log = log_func
    self.excluded_paths = set()
    self.included_paths = set()
    self.excluded_services = []
    self.restartable_services = []


  def __set_device_from_ramdev(self):
    for i in (_RAMDEV, self.__make_zone_path(_ZONEROOT, _RAMDEV)):
      try:
        with open(i, 'r') as f:
          self.device = f.read()
          return
      except FileNotFoundError:
        self.device = None


  def __get_pfs_mounts(self, path_prefix = ''):
    mounts = []
    with open('/proc/mounts', 'r') as f:
      for _, i, kind, options, *_ in map(shlex.split, f.readlines()):
        a = os.path.abspath(i)
        if any(((a == (path_prefix + os.path.sep + j) or
                a.startswith(path_prefix + os.path.sep + j + os.path.sep)) and
                not any((a.startswith(k + os.path.sep) for k in _EXCLUDED_PFS))
                for j in _PFS)):
          mounts.append((a, kind, options))
    return sorted(mounts)


  def __get_root_device_and_type(self):
    with open('/proc/mounts', 'r') as f:
      for device, mount_point, kind, *_ in map(shlex.split, f.readlines()):
        if mount_point == '/':
          return device, kind


  def __copy_dirs(self, path):
    '''
    Creates a directory within the PivotZone along with any of its parent
    directories if they do not already exist. The directories must also exist
    in the main rootfs. If they do not, FileNotFoundError will be thrown.
    Ownership and permissions will be copied from the rootfs directories to the
    ones in the PivotZone.

    Parameters:
    path: The path of the directory which will be created.

    Returns:
    A set containing all paths which were created in the PivotZone
    '''
    dirs = []
    created = set()
    while not dirs or dirs[0] != path:
      dirs.insert(0, path)
      path = os.path.dirname(path)
    for d in dirs:
      zpath = self.__make_zone_path(_ZONEROOT, os.path.abspath(d))
      try:
        st = os.stat(d, follow_symlinks = False)
        if stat.S_ISLNK(st.st_mode):
          target = os.readlink(d)
          if os.path.abspath(target).split(os.path.sep)[1] in _RESERVED_PATHS:
            raise Exception('included path is in reserved path', zpath)
          os.symlink(target, zpath)
          created.update(
            self.__copy_dirs(os.path.join(os.path.dirname(dirs[-1]), target)))
        elif stat.S_ISDIR(st.st_mode):
          os.mkdir(zpath)
          os.chmod(zpath, stat.S_IMODE(st.st_mode))
        os.chown(zpath, st.st_uid, st.st_gid, follow_symlinks = False)
        created.add(zpath)
      except FileExistsError:
        pass
    return created


  def add_file(self, p):
    if type(p) is str:
      self.included_paths.add(p)
    else:
      for i in p:
        self.included_paths.add(p)


  def add_files(self, p):
    self.add_file(p)


  def excluded_file(self, p):
    if type(p) is str:
      self.excluded_paths.add(p)
    else:
      for i in p:
        self.excluded_paths.add(p)


  def excluded_files(self, p):
    self.excluded_file(p)


  def exclude_service(self, s, user = False):
    if type(s) is str:
      self.excluded_services.append((s, user))
    else:
      for i in s:
        self.excluded_services.append((i, user))


  def exclude_services(self, s, user = False):
    self.exclude_service(s, user)


  def restart_service(self, s, user = False):
    if type(s) is str:
      self.restartable_services.append((s, user))
    else:
      for i in s:
        self.restartable_services.append((i, user))


  def restart_services(self, s, user = False):
    self.restart_service(s, user)


  def copy_into_zone(self, included_paths, excluded_paths = None):
    '''
    Copies a set of path glob patterns into the PivotZone. Existing files will
    not be overriden; a FileExistsError will be thrown if any are encountered.

    Parameters:
    included_paths: A set of glob patterns that match paths in the rootfs which
                    will match the files, directories and symlinks to be copied
                    into the PivotZone
    excluded_paths: An optional set of glob patterns that match paths in the
                    rootfs and in included_paths which will not be copied into
                    the PivotZone
    Returns:
    A set containing all paths which were copied into the PivotZone
    '''
    if self.is_in_zone():
      raise Exception('must be called from outside the pivotzone')
    if not os.path.ismount(_ZONEROOT):
      raise Exception('pivotzone must be built first')
    created = set()
    if excluded_paths is None:
      excluded_paths = set()
    for pattern in included_paths:
      for path in glob.iglob(pattern, include_hidden=True, recursive=True):
        if not any((fnmatch.fnmatch(path, i) for i in excluded_paths)):
          zpath = os.path.abspath(path)
          if zpath.split(os.path.sep)[1] in _RESERVED_PATHS:
            raise Exception('included path is in reserved path', zpath)
          zpath = self.__make_zone_path(_ZONEROOT, zpath)
          try:
            st = os.stat(path, follow_symlinks = False)
          except FileNotFoundError:
            continue
          if stat.S_ISLNK(st.st_mode):
            created.update(self.__copy_dirs(os.path.dirname(path)))
            os.symlink(os.readlink(path), zpath)
            created.add(zpath)
          elif stat.S_ISDIR(st.st_mode):
            created.update(self.__copy_dirs(path))
          elif stat.S_ISREG(st.st_mode):
            created.update(self.__copy_dirs(os.path.dirname(path)))
            open(zpath, 'x').close() # ensure doesn't exist
            shutil.copy2(path, zpath)
            created.add(zpath)
    return created


  def build(self):
    if os.getuid() != 0 or os.getgid() != 0:
      raise Exception('must be root')

    try:
      os.mkdir(_RUN_DIR)
      os.chmod(_RUN_DIR, _ONLY_OWNER_CAN_WRITE)
    except FileExistsError:
      raise Exception(
        'You can have multiple PivotZone configurations but only one can be ' +
        'used at a time. Consider using containers inside your PivotZone.')

    os.mkdir(_ZONEROOT)
    os.chmod(_ZONEROOT, _ONLY_OWNER_CAN_WRITE)

    subprocess.run(['modprobe', 'zram'])
    self.device = subprocess.check_output(['zramctl', '--find']).decode().strip()
    if not self.device.startswith('/dev/zram') or not self.device[9:].isdigit():
      raise Exception('unexpected device from zramctl', self.device)

    for _ in range(RETRY_COUNT):
      p = subprocess.run(['zramctl', self.device,
                           '--algorithm', self.algorithm,
                           '--size', self.size],
                          capture_output = True)
      if p.returncode == 0:
        break
      if 'Device or resource busy' in p.stderr.decode():
        time.sleep(RETRY_DELAY)
      else:
        p.check_returncode()
    p.check_returncode()

    subprocess.check_call(['mkfs.ext4', self.device])
    subprocess.check_call(['mount', self.device, _ZONEROOT])

    self.copy_into_zone(self.included_paths, self.excluded_paths)

    for mpoint, kind, options in self.__get_pfs_mounts():
      self.__copy_dirs(mpoint)
      if kind == 'autofs':
        continue
      zmpoint = self.__make_zone_path(_ZONEROOT, mpoint)
      # if any((zmpoint == os.path.join(_ZONEROOT, i) for i in _SHARED_PFS)):
      #   subprocess.check_call(['mount', '--bind', mpoint, zmpoint])
      # else:
      #   subprocess.check_call(['mount', '-t', kind, '-o', options, 'none',
      #                          self.__make_zone_path(_ZONEROOT, mpoint)])
      subprocess.check_call(['mount', '-t', kind, '-o', options, 'none',
                             self.__make_zone_path(_ZONEROOT, mpoint)])

    self.__copy_dirs(_RUN_DIR)
    ramdev_in_zone = self.__make_zone_path(_ZONEROOT, _RAMDEV)
    with open(ramdev_in_zone, 'x') as f:
      f.write(self.device)

    root_device, root_device_type = self.__get_root_device_and_type()
    rootdev_in_zone = self.__make_zone_path(_ZONEROOT, _ROOTDEV)
    with open(rootdev_in_zone, 'w') as f:
      f.write(shlex.join((root_device, root_device_type)))

    backingroot_in_zone = self.__make_zone_path(_ZONEROOT, _BACKINGROOT)
    os.mkdir(backingroot_in_zone)
    os.chmod(backingroot_in_zone, _ONLY_OWNER_CAN_ACCESS)
    subprocess.check_call(['mount', '--bind', '/', backingroot_in_zone])


  def destroy(self):
    self.__set_device_from_ramdev()
    backingroot_in_zone = self.__make_zone_path(_ZONEROOT, _BACKINGROOT)
    if os.path.ismount(backingroot_in_zone):
      subprocess.check_call(['umount', backingroot_in_zone])
    for i, _, _ in reversed(self.__get_pfs_mounts()):
      zpath = self.__make_zone_path(_ZONEROOT, i)
      if os.path.ismount(zpath):
        subprocess.check_call(['umount', zpath])
    if os.path.ismount(_ZONEROOT):
      subprocess.check_call(['umount', _ZONEROOT])
    if self.device:
      p = subprocess.run(['zramctl', self.device, '--reset'], capture_output = True)
      if 'No such device' not in p.stderr.decode():
        p.check_returncode()
    for i in (_ROOTDEV, _RAMDEV):
      if os.path.exists(i):
        os.remove(i)
    for i in (_BACKINGROOT, _ZONEROOT, _RUN_DIR):
      if os.path.exists(i):
        os.rmdir(i)


  def start_daemon(self):
    args = shlex.split(self.pivotzoned)
    self.exec(args[0], args[1:])


  def build_and_start_daemon(self):
    self.build()
    self.start_daemon()


  def __collate_services_status(self, user = None):
    service_names_of_interest = {
      i[0] for i in filter(lambda i: i[1] == (user is not None),
          {*self.excluded_services, *self.restartable_services})}
    return dict(filter(lambda i: i[0] in service_names_of_interest,
                  self.service_manager.get_active_units(user = user).items()))


  def __load_mounts(self, mounts_path):
    mounts = []
    with open(mounts_path, 'r') as f:
      for device, mount_point, *_ in map(shlex.split, f):
        mounts.append((device, mount_point))
    return mounts


  def __get_per_proc_mounts(self):
    for _ in range(RETRY_COUNT):
      res = []
      try:
        for pid in filter(str.isdigit, os.listdir('/proc')):
          res.append((int(pid), self.__load_mounts(f'/proc/{pid}/mounts')))
        return res
      except OSError as err:
        _err = err
        time.sleep(RETRY_DELAY)
    raise _err


  def enter(self):
    if os.getuid() != 0 or os.getgid() != 0:
      raise Exception('must be root')

    # TODO sanity check - make sure luks keyfile and device? are set before if root is LUKS

    pfsholder_dir = self.make_zone_path(_PFSHOLDER)
    try:
      os.mkdir(pfsholder_dir)
      os.chmod(pfsholder_dir, _ONLY_OWNER_CAN_WRITE)
    except FileExistsError:
      raise Exception('pivotzone already entered')

    cwd = os.getcwd()

    if self.is_in_zone():
      for pid in filter(str.isdigit, os.listdir('/proc')):
        wd = f'/proc/{pid}/cwd'
        path = os.readlink(wd)
        if path == '/':
          os.chroot(wd)
          break

    subprocess.run(['modprobe', 'nbd'])
    subprocess.run(['modprobe', 'vfio-pci'])

    if self.excluded_services or self.restartable_services:
      logged_in_users = self.service_manager.get_logged_in_users()
      self.system_service_statuses = self.__collate_services_status()
      self.user_service_statuses = {i: self.__collate_services_status(i)
                                    for i in logged_in_users}

      for service_name, is_user in [*self.excluded_services,
                                    *self.restartable_services]:
        if is_user:
          for user, statuses in self.user_service_statuses.items():
            if statuses.get(service_name):
              self.service_manager.stop_service(service_name, user = user)
        elif not is_user and self.system_service_statuses.get(service_name):
          self.service_manager.stop_service(service_name)

    # TODO interrupt pivotzoned here

    backingroot_in_zone = self.__make_zone_path(_ZONEROOT, _BACKINGROOT)
    if os.path.ismount(_BACKINGROOT):
      subprocess.check_call(('umount', _BACKINGROOT))
    elif os.path.ismount(backingroot_in_zone):
      subprocess.check_call(('umount', backingroot_in_zone))

    subprocess.check_call(('mount', '--make-rprivate', '/'))
    subprocess.check_call(('pivot_root', _ZONEROOT, backingroot_in_zone))
    os.chroot('/')

    self.log('---- Terminating processes which are still using the drive ----')
    for pid, exe in _get_exes():
      self.log(f'pid: {pid} exe: {exe}')
      if exe.startswith(_BACKINGROOT+os.path.sep):
        sig = signal.SIGTERM
        self.log(f'Sent {sig} to {pid}')
        self.log(f'EXE: {exe}')
        try:
          with open(f'/proc/{pid}/cmdline', 'r') as f:
            self.log('CMDLINE: ' + f.read())
        except FileNotFoundError:
          pass
        try:
          os.kill(pid, sig)
        except ProcessLookupError:
          pass
    self.log('-------------------------------------------------------------\n')

    for i in _PFS:
      backing_path = os.path.join(_BACKINGROOT, i)
      if os.path.ismount(backing_path):
        holder_path = os.path.join(_PFSHOLDER, i)
        os.mkdir(holder_path)
        os.chmod(holder_path, _ONLY_OWNER_CAN_WRITE)
        if i not in _SHARED_PFS:
          subprocess.check_output(('mount', '--move', backing_path, holder_path))

    self.service_manager.force_restart_stuborn_services()

    # Wait until the service manager is back up
    for _ in range(RETRY_COUNT):
      try:
        self.service_manager.get_active_units()
        break
      except Exception:
        time.sleep(RETRY_DELAY)

    # NB: systemd uses a hardcoded path for the system bus socket so the real
    #     rootfs's /run needs to temporarily swap places with the PivotZone's
    #     /run until we're done talking to the init daemon.
    #     See src/shared/bus-util.c in systemd's source
    #     Other init systems also often rely on fifo, sockets, etc in /run too
    run_holder = os.path.join(_PFSHOLDER, 'run')
    zrun_holder = os.path.join('/', _ZRUNHOLDERNAME)
    os.mkdir(zrun_holder)
    subprocess.run(('mount', '--move', '/run', zrun_holder))
    zrun_holder_backingroot = _BACKINGROOT.replace('/run', zrun_holder)
    subprocess.check_output(('mount', '--move',
                              os.path.join(zrun_holder_backingroot, 'run'),
                              '/run'))

    # TODO pivotzoned is also service manager?

    if hasattr(self, 'enter_hook'):
      self.enter_hook()

    self.service_manager.reexec()

    if self.restartable_services:
      logged_in_users = self.service_manager.get_logged_in_users()
      for service_name, is_user in self.restartable_services:
          if is_user:
            for user, statuses in self.user_service_statuses.items() :
              if user in logged_in_users and statuses.get(service_name):
                self.service_manager.restart_service(service_name, user = user)
          elif not is_user and self.system_service_statuses.get(service_name):
            self.service_manager.restart_service(service_name)

    zrun_holder_pfsholder = _PFSHOLDER.replace('/run', zrun_holder)
    subprocess.check_output(('mount', '--move',
                              '/run',
                              os.path.join(zrun_holder_pfsholder, 'run')))
    subprocess.check_output(('mount', '--move', zrun_holder, '/run'))
    os.rmdir(zrun_holder)

    mounts = self.__load_mounts('/proc/mounts')

    # TODO unmount non-root drives

    for _ in range(RETRY_COUNT):
      p = subprocess.run(('umount', _BACKINGROOT))
      self.log(f'umount _BACKINGROOT ret = {p.returncode}')
      if p.returncode == 0:
        break
      time.sleep(RETRY_DELAY)
    p.check_returncode()

    for device, mount_point in mounts:
      if mount_point == _BACKINGROOT and device.startswith('/dev/mapper/'):
        cryptsetup = shutil.which('cryptsetup')
        if cryptsetup:
          for _ in range(RETRY_COUNT):
            try:
              for pid, mounts in self.__get_per_proc_mounts():
                if any(d == device for d,m in mounts):
                  self.log(f'crypt try kill {pid}')
                  try:
                    with open(f'/proc/{pid}/cmdline', 'r') as f:
                      self.log(f'CMDLINE: {f.read()}')
                  except OSError:
                    pass
                  os.kill(pid, signal.SIGTERM)
              self.log(f'crypt success')
              break
            except OSError:
              self.log(f'crypt fail')
              time.sleep(RETRY_DELAY)
          name = device[12:]
          busy_msgs = ('Device or resource busy', 'is still in use')
          for _ in range(RETRY_COUNT):
            p = subprocess.run((cryptsetup, 'close', name), capture_output = True)
            self.log(f'crypt close attempt = {p}')
            if all(i not in p.stderr.decode() for i in busy_msgs):
              break
            time.sleep(RETRY_DELAY)
          if any(i in p.stderr.decode() for i in busy_msgs):
            raise Exception('cryptsetup could not remove busy device', device)

    os.chdir(cwd if os.path.isdir(cwd) else '/')
    self.log(f'enter done')


  def exit(self):
    if os.getuid() != 0 or os.getgid() != 0:
      raise Exception('must be root')

    if not self.is_in_zone():
      raise Exception('exit can only be called within an entered pivotzone')

    cwd = os.getcwd()

    with open(_ROOTDEV, 'r') as f:
      root_device, root_device_type = shlex.split(f.read())

    # TODO a bunch of daemon stuff here

    subprocess.check_call(('mount', '-t', root_device_type,
                           root_device, _BACKINGROOT))

    subprocess.check_call(('mount', '--make-rprivate', '/'))

    for i in os.listdir(_PFSHOLDER):
      backing_path = os.path.join(_BACKINGROOT, i)
      zpath = os.path.join(_ZONEROOT, i)
      # subprocess.check_output(('mount', '--bind', zpath, backing_path))
      holder_path = os.path.join(_PFSHOLDER, i)
      subprocess.check_output(('mount', '--move', holder_path, backing_path))
      os.rmdir(holder_path)

    subprocess.check_call(('pivot_root', _BACKINGROOT, _BACKINGROOT+_ZONEROOT))
    subprocess.check_call(('mount', '--make-rshared', '/'))
    os.chdir(cwd if os.path.isdir(cwd) else '/')

    self.service_manager.reexec()
    self.service_manager.force_restart_stuborn_services()

    self.log(f'system_service_statuses = {self.system_service_statuses}')

    if self.excluded_services or self.restartable_services:
      logged_in_users = None
      user_service_statuses = {}
      if hasattr(self, 'user_service_statuses'):
        user_service_statuses = self.user_service_statuses

      for service_name, is_user in reversed([*self.excluded_services,
                                             *self.restartable_services]):
        if is_user:
          if logged_in_users is None:
            logged_in_users = self.service_manager.get_logged_in_users()
          for user, statuses in user_service_statuses.items() :
            if statuses.get(service_name):
              self.service_manager.restart_service(service_name, user = user)
        elif not is_user and getattr(self, 'system_service_statuses', {}).get(service_name):
          self.service_manager.restart_service(service_name)

    backingroot_in_zone = self.__make_zone_path(_ZONEROOT, _BACKINGROOT)
    subprocess.check_call(['mount', '--bind', '/', backingroot_in_zone])
    os.rmdir(_ZONEROOT+_PFSHOLDER)


  def wait_for_nbd_and_tell_daemon(self, ndb_host):
    pass


  def exec(self, file, args):
    cwd = os.path.abspath(os.getcwd())
    cwd = cwd[len(_ZONEROOT):] if cwd.startswith(_ZONEROOT) else '/'
    os.chroot(_ZONEROOT)
    os.chdir(cwd)
    os.execvp(file, args)


  def is_in_zone(self):
    if not hasattr(self, 'device') or not self.device:
      self.__set_device_from_ramdev()
    root_device, _ = self.__get_root_device_and_type()
    return self.device == root_device


  def is_nv_ready(self):
    return os.path.exists(_NVREADYFLAG)


  def __make_zone_path(self, root, path):
    if hasattr(os.path, 'splitroot'):
      p = os.path.splitroot(path)[2]
    else:
      p = os.path.splitdrive(path)[1]
      p = path[len(os.path.sep):] if path.startswith(os.path.sep) else path
    return os.path.join(root, p)


  def make_zone_path(self, path):
    root = '/' if self.is_in_zone() else _ZONEROOT
    return self.__make_zone_path(root, path)


  def get_real_root_device(self):
    for i in (_ROOTDEV, self.__make_zone_path(_ZONEROOT, _ROOTDEV)):
      try:
        with open(i, 'r') as f:
          root_device, _ = shlex.split(f.read())
          return root_device
      except FileNotFoundError:
        pass
    root_device, _ = self.__get_root_device_and_type()
    return root_device

