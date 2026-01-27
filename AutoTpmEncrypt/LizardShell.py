# Copied from the guide's FAQ:
# Q: What is LizardShell.py?
#
# A: LizardShell is a small text based terminal emulator combined with an on-screen keyboard designed to be run while the Steam Deck's controls are in "Lizard Mode" (https://www.reddit.com/r/SteamController/comments/41329r/eli5_what_is_lizard_mode). When it starts, the Steam client disables Lizard Mode and maps the Deck's controls to the desktop controller layout, the layout for whatever game you're playing, etc. Lizard Mode is the default mode that the Deck's controls start in and it's designed as a fallback in case Steam doesn't load correctly. Lizard Mode maps the D-Pad to the arrow keys, the A button to Enter, the right touch pad to the mouse, etc. LizardShell is designed to enable controlling a terminal using the Deck's D-Pad and A button while the Deck is still in Lizard Mode. LizardShell runs from a basic VGACON console and its original purpose was to avoid the need to install a window manager, on screen keyboard program and all of their dependencies to the recovery partition in order to save space and keep the recovery partition small. LizardShell is about 80% complete. It works but there are more bugs in it than were worth fixing. I've included LizardShell as a curiosity since some people may find it interesting. I eventually abandoned it in favor of just using Fluxbox and CoreKeyboard. Both are small but there is still some room for improvement regarding shrinking the space needed for the recovery partition.


import sys, os, tty, pty, termios, subprocess, threading, string

DEFAULT_FG_COLOR = 32
DEFAULT_BG_COLOR = 40
KEY_HIGHLIGHT_BG_COLOR = 42
CTRL_TOGGLED_BG_COLOR = 47

KEYBOARD_LAYOUT = [
  ['Esc'] + list('`123456890-=') + ['Backspace', 'Redraw'],
  ['Tab'] + list('qwertyuiop[]\\') + ['Home', 'End'],
  ['Caps'] + list('asdfghjkl;\'') + ['Enter', 'PgUp', '/\\'],
  ['Ctrl', 'Shift'] + list('zxcvbnm,./') + ['Space', 'PgDn', '<=', '\\/', '=>'],
]

MAPABLE_KEYS = {
  'Esc': 27,
  'Tab': 9,
  'Space': 32,
  'Enter': 13,
  '/\\': '\x1b[A',
  '\\/': '\x1b[B',
  '=>': '\x1b[C',
  '<=': '\x1b[D',
  'Home': '\x1b[1~',
  'End': '\x1b[4~',
  'PgUp': '\x1b[5~',
  'PgDn': '\x1b[6~',
  'Del': '\x1b[3~',
  'Redraw': '\x0C',
}

SHIFTED_KEYS = {
  '1':'!', '2':'@', '3':'#', '4':'$', '5':'%', '6':'^', '7':'&', '8':'*', '9':'(', '0':')', '-':'_', '=':'+',
  '[':'{', ']':'}', '\\':'|', ';':':', '\'':'"', ',':'<', '.':'>', '/':'?', '`':'~', '\'': '"',
}
SHIFTED_KEYS.update({i:i.upper() for i in string.ascii_lowercase})

def init():
  state = {
	'width': -1, 'height': -1,
	'screen': [],
        'screen_x': 0, 'screen_y': 0,
        'fg_color': DEFAULT_FG_COLOR, 'bg_color': DEFAULT_BG_COLOR,
	'key_x': 0, 'key_y': 0,
	'lock': threading.Lock()
  }

  state['wrapper_fd'], state['shell_fd'] = pty.openpty()

  shell = os.environ.get('LIZARDSHELL')
  if not shell:
    shell = os.environ.get('SHELL')
  if not shell:
    shell = '/bin/bash'

  env = os.environ.copy()
  env['LIZARDSHELL_RUNNING'] = '1'
  state['shell'] = subprocess.Popen(shell,
                                    stdin = state['shell_fd'],
                                    stdout = state['shell_fd'],
                                    stderr = state['shell_fd'],
                                    close_fds = True,
                                    env = env)
  return state

def new_default_char():
  return {'char': ' ', 'fg_color': DEFAULT_FG_COLOR, 'bg_color': DEFAULT_BG_COLOR}

def new_screen(state):
  return [[new_default_char() for _ in range(state['width'])] for _ in range(state['height'])]

def move_real_cursor(state, x, y):
  assert(state['lock'].locked())
  if x != state.get('real_x') or y != state.get('real_y'):
    sys.stdout.write('\x1b[' + str(y+1) + ';' + str(x+1) + 'H')
    sys.stdout.flush()
    state['real_x'], state['real_y'] = x, y

def set_real_color(state, color):
  assert(state['lock'].locked())
  kind = 'real_fg_color' if color < 40 else 'real_bg_color'
  if state.get(kind) != color:
    sys.stdout.write('\x1b[1;' + str(color) + 'm')
    sys.stdout.flush()
    state[kind] = color

def reset_real_color(state):
  assert(state['lock'].locked())
  sys.stdout.write('\x1b[0m')
  sys.stdout.flush()
  state['real_fg_color'] = None
  state['real_bg_color'] = None

def redraw_screen(state):
  state['screen'] = state['screen'][:state['height']]
  state['screen'] = [row[:state['width']] + [new_default_char() for _ in range(state['width']-len(row))] for row in state['screen']]
  state['screen'] += [[new_default_char() for _ in range(state['width'])] for _ in range(state['height']-len(state['screen']))]
  move_real_cursor(state, 0, 0)
  for row in state['screen']:
    for c in row:
      set_real_color(state, c['fg_color'])
      set_real_color(state, c['bg_color'])
      sys.stdout.write(c['char'])
  sys.stdout.write('\n')
  sys.stdout.flush()
  state['real_x'], state['real_y'] = 0, state['height']

def redraw_keyboard(state):
  move_real_cursor(state, 0, state['height']+1)
  set_real_color(state, DEFAULT_FG_COLOR)
  set_real_color(state, DEFAULT_BG_COLOR)
  for y_idx, row in enumerate(KEYBOARD_LAYOUT):
    if y_idx > 0:
      sys.stdout.write('\n')
    for x_idx, key in enumerate(row):
      if x_idx > 0:
        sys.stdout.write(' ')
      if x_idx == state['key_x'] and y_idx == state['key_y']:
        set_real_color(state, CTRL_TOGGLED_BG_COLOR if state.get('ctrl_enabled') else KEY_HIGHLIGHT_BG_COLOR)
      sys.stdout.write(SHIFTED_KEYS[key] if state.get('shift_enabled') and key in SHIFTED_KEYS else key)
      if x_idx == state['key_x'] and y_idx == state['key_y']:
        set_real_color(state, DEFAULT_BG_COLOR)
  sys.stdout.flush()
  state['real_x'] = None
  state['real_y'] = None

def redraw_if_terminal_resized(state):
  width, height = os.get_terminal_size()
  height = height - (len(KEYBOARD_LAYOUT)+1)
  if height < 1 or max((len(' '.join(row)) for row in KEYBOARD_LAYOUT)) > width:
    sys.stdout.write('Terminal too small to fit screen and keyboard. Resize if possible.')
    sys.stdout.flush()
    return
  if width != state['width'] or height != state['height']:
    state['width'], state['height'] = width, height
    redraw_screen(state)
    set_real_color(state, DEFAULT_FG_COLOR)
    set_real_color(state, DEFAULT_BG_COLOR)
    sys.stdout.write(('-'*width) + '\n')
    state['real_x'] = 0
    state['real_y'] = state['height']
    redraw_keyboard(state)


KNOWN_BUT_IGNORED_ESCAPE_SEQUENCES = {
  '[?2004h', # Bracketed-paste enable
  '[?2004l', # Bracketed-paste disable
  '[?7727h', # Application escape mode
  '[>q',     # XTVERSION (short)
  '[>0q',    # XTVERSION (long)
  '[?7h',    # auto wrap mode
  '[4l',     # set to replace mode

  '[?1h',
  '[?1l',
  '[?12l',
  '[?1000l', # Mouse stuff
  '[?1002l', # Mouse stuff
  '[?1003l', # Mouse stuff
  '[?1006l', # Mouse stuff
  '[?1005l', # Mouse stuff
}


def handle_escape_sequence(state):
  buf = ''
  while True:
    c = os.read(state['wrapper_fd'], 1).decode(errors='ignore')
    if not buf and c == '[':
      buf += c
    elif not buf:
      return
    elif c in '0123456789;?!>':
      buf += c
    else:
      buf += c
      break

  # Move cursor to column
  if buf[-1] == 'G':
    state['screen_x'] = (int(buf[1:-1])-1) if len(buf) > 2 else 0
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Move cursor to row
  elif buf[-1] == 'd':
    state['screen_y'] = (int(buf[1:-1])-1) if len(buf) > 2 else 0
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Move cursor to coordinates
  elif buf[-1] == 'H':
    if buf == '[H':
      x, y = 1, 1
    else:
      y, x = map(int, buf[1:-1].split(';'))
    state['screen_x'] = x-1
    state['screen_y'] = y-1

  # Move cursor right
  elif buf[-1] == 'C':
    state['screen_x'] += int(buf[1:-1]) if len(buf) > 2 else 1
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Toggle cursor visibility
  elif buf in ('[?25h', '[?25l'):
    sys.stdout.write('\x1b' + buf)
    sys.stdout.flush()

  # Erase from cursor to end of line
  elif buf in ('[K', '[0K'):
    state['screen'][state['screen_y']] = state['screen'][state['screen_y']][:state['screen_x']] + [new_default_char() for _ in range(state['width']-state['screen_x'])]
    sys.stdout.write(' '*(state['width']-state['screen_x']))
    state['real_x'] = None
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Erase to left of cursor
  elif buf == '[1K':
    for i in range(state['screen_x']):
      state['screen'][state['screen_y']][i] = new_default_char()
    move_real_cursor(state, 0, state['screen_y'])
    sys.stdout.write(' '*state['screen_x'])
    sys.stdout.flush()
    state['real_x'] = state['screen_x']

  # Erase n characters to the right of the cursor
  elif buf[-1] == 'X':
    for i in range(state['width'] - state['screen_x']):
      state['screen'][state['screen_y']][state['screen_x'] + i] = new_default_char()
    move_real_cursor(state, state['screen_x'] + 1, state['screen_y'])
    sys.stdout.write(' '*(state['width']-state['screen_x']))
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Erase below
  elif buf in ('[J', '[0J'):
    state['screen'] = state['screen'][:state['screen_y']]
    redraw_screen(state)

  # Clear screen
  elif buf == '[2J':
    state['screen'] = new_screen(state)
    redraw_screen(state)

  # Delete n characters
  elif buf[-1] == 'P':
    n = int(buf[1:-1]) if len(buf) > 2 else 1
    move_real_cursor(state, state['screen_x'], state['screen_y'])
    sys.stdout.write(' '*n)
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Scroll up n lines
  elif buf[-1] == 'S':
    n = int(buf[1:-1])
    state['screen'] = state['screen'][n:] + [[new_default_char() for _ in range(state['width'])] for _ in range(n)]
    redraw_screen(state)

  # Cursor up n times
  elif buf[-1] == 'A':
    n = int(buf[1:-1]) if len(buf) > 2 else 1
    state['screen_y'] -= n
    if state['screen_y'] < 0:
      state['screen_y'] = 0
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Cursor down n times
  elif buf[-1] == 'B':
    n = int(buf[1:-1]) if len(buf) > 2 else 1
    state['screen_y'] += n
    if state['screen_y'] >= state['height']:
      state['screen_y'] = state['height'] - 1
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Cursor right n times
  elif buf[-1] == 'C':
    n = int(buf[1:-1]) if len(buf) > 2 else 1
    state['screen_x'] += n
    if state['screen_x'] >= state['width']:
      state['screen_x'] = state['width']
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Cursor left n times
  elif buf[-1] == 'D':
    n = int(buf[1:-1]) if len(buf) > 2 else 1
    state['screen_x'] -= n
    if state['screen_x'] < 0:
      state['screen_x'] = 0
    move_real_cursor(state, state['screen_x'], state['screen_y'])

  # Set scroll region (incomplete)
  elif buf[-1] == 'r':
    try:
      top, bottom = map(int, buf[1:-1].split(';'))
      state['screen_y'] = top
      move_real_cursor(state, state['screen_x'], state['screen_y'])
    except ValueError:
      pass

  # Enable alt buffer
  elif buf == '[?1049h':
    if 'alt_screen' not in state:
      state['alt_screen'] = new_screen(state)
    if not state.get('using_alt_buf'):
      state['screen'], state['alt_screen'] = state['alt_screen'], state['screen']
    state['using_alt_buf'] = True
    redraw_if_terminal_resized(state)

  # Disable alt buffer
  elif buf == '[?1049l':
    if state.get('using_alt_buf'):
      state['screen'], state['alt_screen'] = state['alt_screen'], state['screen']
      state['using_alt_buf'] = False
      redraw_if_terminal_resized(state)

  # Send Device Attributes (Secondary DA)
  elif buf in ('[>c', '[>0c'):
    os.write(state['wrapper_fd'], b'\x1b[>0;0;0c')

  # Text Color and Style
  elif buf[-1] == 'm':
    try:
      colors = list(map(int, buf[1:-1].split(';')))
    except ValueError:
      colors = [None]

    # Reset to default style
    if colors[0] == 0:
      state['fg_color'] = DEFAULT_FG_COLOR
      state['bg_color'] = DEFAULT_BG_COLOR

    # Use specified colors
    elif colors[0] == 1:
      for color in colors[1:]:
        if color > 29 and color < 40:
          state['fg_color'] = color
        elif color > 39 and color < 50:
          state['bg_color'] = color

  # XTWINOPS, ignored
  elif buf[-1] == 't':
    pass

  elif buf in KNOWN_BUT_IGNORED_ESCAPE_SEQUENCES:
    pass

  else:
    pass
    # Uncomment the line below to break when an unhandled sequence is hit
    #breakpoint()
    # with open('/tmp/unhandled_esc.txt', 'ab') as f:
      # f.write(b'UNHANDLED '+buf.encode()+b'\n')

def screen_worker(state):
  while state['shell'].poll() is None:
    c = os.read(state['wrapper_fd'], 1).decode(errors='ignore')
    with state['lock']:
      redraw_if_terminal_resized(state)

    if c == '\x1b':
      with state['lock']:
        handle_escape_sequence(state)
    elif c == '\n':
      state['screen_x'] = 0
      state['screen_y'] += 1
    elif c == '\r':
      state['screen_x'] = 0
    elif c == '\b':
      with state['lock']:
        screen_char = state['screen'][state['screen_y']][state['screen_x']]
        screen_char['char'] = ' '
        move_real_cursor(state, state['screen_x'], state['screen_y'])
        set_real_color(state, screen_char['fg_color'])
        set_real_color(state, screen_char['bg_color'])
        sys.stdout.write(' ')
        state['screen_x'] -= 1
        move_real_cursor(state, state['screen_x'], state['screen_y'])
    elif c.isprintable():
      screen_char = state['screen'][state['screen_y']][state['screen_x']]
      screen_char['char'] = c
      screen_char['fg_color'] = state['fg_color']
      screen_char['bg_color'] = state['bg_color']
      with state['lock']:
        move_real_cursor(state, state['screen_x'], state['screen_y'])
        set_real_color(state, state['fg_color'])
        set_real_color(state, state['bg_color'])
        sys.stdout.write(c)
        sys.stdout.flush()
      state['screen_x'] += 1

    if state['screen_x'] < 0:
      state['screen_x'] = 0
    elif state['screen_x'] >= state['width']:
      state['screen_x'] = 0
      state['screen_y'] += 1

    if state['screen_y'] >= state['height']:
      state['screen_y'] = state['height'] - 1
      state['screen'] = state['screen'][1:] + [[new_default_char() for _ in range(state['width'])]]
      with state['lock']:
        redraw_screen(state)
    elif c.isprintable() and c not in '\n\r\b':
      state['real_x'], state['real_y'] = state['screen_x'], state['screen_y']

def redraw_current_key(state, selected):
  real_y = state['height'] + 1 + state['key_y']
  real_x = len(' '.join(KEYBOARD_LAYOUT[state['key_y']][:state['key_x']]))
  if real_x > 0:
    real_x += 1
  key = KEYBOARD_LAYOUT[state['key_y']][state['key_x']]
  move_real_cursor(state, real_x, real_y)
  set_real_color(state, DEFAULT_FG_COLOR)
  if not selected:
    set_real_color(state, DEFAULT_BG_COLOR)
  elif state.get('ctrl_enabled'):
    set_real_color(state, CTRL_TOGGLED_BG_COLOR)
  else:
    set_real_color(state, KEY_HIGHLIGHT_BG_COLOR)
  sys.stdout.write(SHIFTED_KEYS[key] if key in SHIFTED_KEYS and state.get('shift_enabled') else key)
  state['real_x'] += len(key)

def keyboard_worker(state):
  while state['shell'].poll() is None:
    c = sys.stdin.read(1)
    with state['lock']:
      redraw_if_terminal_resized(state)
    if c == '\n':
      key = KEYBOARD_LAYOUT[state['key_y']][state['key_x']]
      if key == 'Backspace':
        with state['lock']:
          pass
        os.write(state['wrapper_fd'], b'\b')
      elif key == 'Ctrl':
        with state['lock']:
          state['ctrl_enabled'] = not state.get('ctrl_enabled')
          redraw_current_key(state, True)
          move_real_cursor(state, state['screen_x'], state['screen_y'])
      elif key == 'Shift':
        with state['lock']:
          state['shift_enabled'] = not state.get('shift_enabled')
          if not state['shift_enabled']:
            state['caps_enabled'] = False
          redraw_keyboard(state)
          move_real_cursor(state, state['screen_x'], state['screen_y'])
      elif key == 'Caps':
        with state['lock']:
          state['caps_enabled'] = not state.get('caps_enabled')
          state['shift_enabled'] = state['caps_enabled']
          redraw_keyboard(state)
          move_real_cursor(state, state['screen_x'], state['screen_y'])
      elif key in MAPABLE_KEYS:
        key = MAPABLE_KEYS[key]
        if type(key) is int:
          os.write(state['wrapper_fd'], chr(key).encode())
        elif type(key) is str:
          os.write(state['wrapper_fd'], key.encode())
        else:
          breakpoint()
      else:
        if state.get('ctrl_enabled'):
          with state['lock']:
            state['ctrl_enabled'] = False
            redraw_current_key(state, True)
            move_real_cursor(state, state['screen_x'], state['screen_y'])
            if ord(key) > 96 and ord(key) < 123:
              os.write(state['wrapper_fd'], chr(ord(key) - 96).encode())
        elif state.get('shift_enabled') and key in SHIFTED_KEYS:
          os.write(state['wrapper_fd'], SHIFTED_KEYS[key].encode())
          with state['lock']:
            if not state.get('caps_enabled'):
              state['shift_enabled'] = False
              redraw_keyboard(state)
        else:
          os.write(state['wrapper_fd'], key.encode())
    elif c == '\x1b':
      c = sys.stdin.read(1)
      if c == '[':
        c = sys.stdin.read(1)

        if c in 'ABCD':
          with state['lock']:
            redraw_current_key(state, False)

            if   c == 'A': state['key_y'] -= 1
            elif c == 'B': state['key_y'] += 1
            elif c == 'C': state['key_x'] += 1
            elif c == 'D': state['key_x'] -= 1

            if state['key_y'] < 0:
              state['key_y'] = len(KEYBOARD_LAYOUT) - 1
            elif state['key_y'] >= len(KEYBOARD_LAYOUT):
              state['key_y'] = 0

            if state['key_x'] < 0:
              state['key_x'] = len(KEYBOARD_LAYOUT[state['key_y']]) - 1
            elif state['key_x'] >= len(KEYBOARD_LAYOUT[state['key_y']]):
              state['key_x'] = 0

            redraw_current_key(state, True)
            move_real_cursor(state, state['screen_x'], state['screen_y'])

def main():
  state = init()

  stdin_fd = sys.stdin.fileno()
  old_attr = termios.tcgetattr(stdin_fd)
  tty.setcbreak(sys.stdin)

  state['old_attr'] = old_attr

  sys.stdout.write('\x1b[2J')
  threading.Thread(target=screen_worker, args=(state,), daemon=True).start()
  threading.Thread(target=keyboard_worker, args=(state,), daemon=True).start()

  state['shell'].wait()

  with state['lock']:
    reset_real_color(state)
    termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_attr)
    sys.exit(state['shell'].returncode)

if __name__ == '__main__' and not os.environ.get('LIZARDSHELL_RUNNING'):
  main()
