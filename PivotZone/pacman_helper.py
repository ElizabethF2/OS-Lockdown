import os, re, subprocess, functools

@functools.cache
def _get_info_for_all_packages():
  return subprocess.check_output(('pacman', '-Qi')).decode().splitlines()


@functools.cache
def get_dependent_packages(packages_name):
  packages = {packages_name}
  lines = _get_info_for_all_packages()
  start_len = 0
  last_was_required_by = False
  while len(packages) > start_len:
    start_len = len(packages)
    for line in lines:
      m = re.match(r'^Required By\s*:\s*(.+)', line)
      if m or (last_was_required_by and ':' not in line):
        if any((i in packages for i in (m.group(1) if m else line).split())):
          packages.add(current_package)
          last_was_required_by = True
          continue
      last_was_required_by = False
      m = re.match(r'^Name\s*:\s*(.+)', line)
      if m:
        current_package = m.group(1)
        continue
  return packages


@functools.cache
def _get_files_from_package(packages_name):
  o = subprocess.check_output(('pacman', '-Ql', packages_name)).decode()
  return {i[len(packages_name)+1:] for i in
      filter(lambda i: i.startswith(packages_name + ' '), o.splitlines())}


def get_files_from_package(packages_name, include_dependencies = True):
  packages = (packages_name,)
  if include_dependencies:
    packages = get_dependent_packages(packages_name)
  files = set()
  for package in packages:
    files.update(_get_files_from_package(package))
  return files


def disable_pacman_systemd_units_within_zone(coordinator):
  units = subprocess.check_output(('systemctl', 'list-units')).decode()
  for line in filter(bool, units.splitlines()):
    unit = line.split()[0]
    if 'listening' in line and 'pacman' in unit:
      # subprocess.check_call(('systemctl', 'mask', unit))  # TODO cleanup
      mask_file = os.path.join('/etc/systemd/system', unit)
      os.symlink('/dev/null', coordinator.make_zone_path(mask_file))

