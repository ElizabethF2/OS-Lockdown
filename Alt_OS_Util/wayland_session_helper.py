#!/usr/bin/env python3

import sys, os, subprocess, re, shlex, json, tomllib

def get_cmdlines_for_current_user():
  cmdlines = set()
  current_uid = os.getuid()
  for pid in os.listdir('/proc'):
    try:
      with open(f'/proc/{pid}/status', 'r') as f:
        lines = f.read().splitlines()
      uid = list(filter(lambda i: i.startswith('Uid:'), lines))[0]
      uid = int(uid.split()[1])
      if uid != current_uid:
        continue
      with open(f'/proc/{pid}/cmdline', 'r') as f:
        cmdlines.add(shlex.join(f.read().split('\x00')[:-1]))
    except (PermissionError, FileNotFoundError, NotADirectoryError):
      pass
  return cmdlines

def load_config():
  path = os.environ.get('WAYLAND_SESSION_HELPER_CONFIG')
  if not path:
    cfg_home = os.environ.get('XDG_CONFIG_HOME')
    if not cfg_home:
      cfg_home = os.path.join('~', '.config')
    path = os.path.join(cfg_home, 'wayland_session_helper.toml')
  with open(os.path.expanduser(path), 'rb') as f:
    return tomllib.load(f)

def get_state_path(config):
  path = config.get('state_path')
  if not path:
    state_home = os.environ.get('XDG_STATE_HOME')
    if not state_home:
      state_home = os.path.join('~', '.local', 'state')
    path = os.path.join(state_home, 'wayland_session_helper.json')
  return os.path.expanduser(path)

def save():
  config = load_config()
  cmdlines = get_cmdlines_for_current_user()
  running_programs = {}
  for program, meta in config['programs'].items():
    p = meta['cmdline_pattern']
    matching_cmdlines = list(filter(lambda c: re.match(p, c), cmdlines))
    if len(matching_cmdlines) > 0:
      running_programs[program] = {'cmdlines': matching_cmdlines}
  state = {'running_programs': running_programs}
  with open(get_state_path(config), 'w') as f:
    json.dump(state, f)
  return 0

def relaunch(pmeta, state_path):
  relaunch_command = pmeta['relaunch_command']
  cmd = relaunch_command.format(state_path = state_path)
  kwargs = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
  if pmeta.get('shell'):
    kwargs['shell'] = True
  if hasattr(subprocess, 'DETACHED_PROCESS'):
    kwargs['creationflags'] = subprocess.DETACHED_PROCESS
  else:
    kwargs['start_new_session'] = True
  return subprocess.Popen(shlex.split(cmd), **kwargs)

def restore():
  config = load_config()
  state_path = get_state_path(config)
  try:
    with open(state_path, 'r') as f:
      state = json.load(f)
  except FileNotFoundError:
    return 0
  running_programs = state.get('running_programs')
  relaunched_programs = []
  for program, meta in running_programs.items():
    pmeta = config['programs'][program]
    relaunched_programs.append({'proc': relaunch(pmeta, state_path),
                                'program': program,
                                'pmeta': pmeta})
  retry_delay = config.get('check_delay', 1)
  for _ in range(config.get('check_count', 10)):
    import time
    time.sleep(retry_delay)
    ok_programs = 0
    for p in relaunched_programs:
      pmeta = p['pmeta']
      if not pmeta.get('check', True):
        ok_programs += 1
        continue
      ret = p['proc'].poll()
      if ret == 0:
        ok_programs += 1
      elif ret is not None:
        p['proc'] = relaunch(pmeta, state_path)
    if ok_programs == len(relaunched_programs):
      break
  if not config.get('keep_state_after_restore'):
    os.remove(state_path)
  return 0

def main():
  if len(sys.argv) < 2:
    print('Missing command')
    return 1
  cmd = sys.argv[1]
  if cmd == 'list':
    print('\n'.join(get_cmdlines_for_current_user()))
    return 0
  elif cmd == 'save':
    return save()
  elif cmd == 'restore':
    return restore()
  else:
    print('Invalid command:', cmd)
    return 1

if __name__ == '__main__':
  sys.exit(main())
