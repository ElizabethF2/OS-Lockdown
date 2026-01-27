import sys, os, shlex, signal

def check(search_substr):
  try:
    ref_st_dev = os.stat('/run/PivotZone/backingroot').st_dev
  except FileNotFoundError:
    ref_st_dev = None
  print(f'ref_st_dev = {ref_st_dev}\n')
  for i in os.listdir('/proc'):
    if i.isdigit():
      with open(f'/proc/{i}/mounts', 'r') as f: mounts = f.readlines()
      with open(f'/proc/{i}/maps', 'r') as f: maps = f.readlines()
      matching = []
      matching_mounts = ['MOUNT: ' + i for i in filter(lambda i: search_substr in i, mounts)]
      if len(matching_mounts) > 1:
        matching += matching_mounts
      matching += ['MAP: ' + i for i in filter(lambda i: search_substr in i, maps)]
      cwd = os.readlink(f'/proc/{i}/cwd')
      if search_substr in cwd:
        matching.append('CWD: ' + cwd)
      root = os.readlink(f'/proc/{i}/root')
      if search_substr in root:
        matching.append('ROOT: ' + root)
      try:
        exe = os.readlink(f'/proc/{i}/exe')
        if search_substr in exe:
          matching.append('EXE: ' + exe)
      except FileNotFoundError:
        pass
      for j in os.listdir(f'/proc/{i}/fd'):
        try:
          target = os.readlink(f'/proc/{i}/fd/{j}')
          st = os.stat(f'/proc/{i}/fd/{j}')
        except FileNotFoundError:
          target = ''
        if search_substr in target:
          matching.append(f'FD (TARGET): {i}:{j} {target}')
        if st.st_dev == ref_st_dev:
          matching.append(f'FD (ST_DEV): {i}:{j} {target}')
      if len(matching) > 0:
        print('PID:', i)
        try:
          with open(f'/proc/{i}/cmdline','r') as f:
            cmdline = shlex.join(f.read().split('\x00'))
        except FileNotFoundError:
          cmdline = '!!! Error Getting CMDLINE !!!'
        print('CMDLINE:', cmdline)
        [print(i.strip()) for i in matching]
        if any((i in sys.argv[:-1] for i in ('-k', '--kill'))):
          sig = tuple((getattr(signal, 'SIG'+i[1:]) if i[0] == '-' and hasattr(signal, 'SIG'+i[1:]) else signal.SIGTERM) for i in sys.argv[-1])[0]
          print(f'Killing PID {i} with {repr(sig)}')
          try:
            os.kill(int(i), sig)
            print('Success!')
          except Exception as ex:
            print('Failed: ' + repr(ex))
        print('')


if __name__ == '__main__':
  if os.getuid() != 0:
    print('Warning: Not running as root!')
    print('         Script may error out or not show all results.')
    print('         Re-run as root for better results.')
  check(sys.argv[-1] if len(sys.argv) > 1 else 'backing')
