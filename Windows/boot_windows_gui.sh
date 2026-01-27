#!/bin/sh

printf BootWindowsGUI >> /proc/$$/comm

show_python_prompt ()
{
python - <<EOF
import sys, qtpy.QtWidgets
a = qtpy.QtWidgets.QApplication(sys.argv)
m = qtpy.QtWidgets.QMessageBox()
r = m.question(m,
               'Windows',
               'Reboot to Windows?',
               m.StandardButton.Yes | m.StandardButton.No)
sys.exit(101 if r == m.StandardButton.Yes else 9)
EOF
ret="$?"
}

type simplemenu 2>/dev/null >/dev/null
if [ "$?" = "0" ] ; then
  simplemenu \
    'Auto Sync and Reboot to Windows' \
    'Manual Sync and Reboot to Windows' \
    'Reboot to Windows without Syncing' \
    'Check Seal' \
    'Cancel'
  ret="$?"
  if [ "$ret" = "4" ] ; then
    exit 1
  fi
  if [ "$ret" = "0" ] ; then
    prbsync auto && sudo /usr/bin/python3 -I /root/.local/bin/boot_windows
  fi
  if [ "$ret" = "1" ] ; then
    prbsync sync && sudo /usr/bin/python3 -I /root/.local/bin/boot_windows
  fi
  if [ "$ret" = "2" ] ; then
    sudo /usr/bin/python3 -I /root/.local/bin/boot_windows --nosync
  fi
  if [ "$ret" = "3" ] ; then
    sudo IGNORE_IF_ON_BATTERY=1 /usr/bin/python3 -I \
      /root/.local/bin/auto_tpm_encrypt --ensure_no_os_are_unsealed
    printf '\n\n\n'
    sudo IGNORE_IF_ON_BATTERY=1 /usr/bin/python3 -I \
      /root/.local/bin/auto_tpm_encrypt --ensure_booted_os_is_sealed
    echo
    echo '[Press ENTER when done]'
    read
  fi
  if [ "$?" != "0" ]; then
    exec ${SHELL:-sh}
  fi
  exit 0
else
  type prbsync 2>/dev/null >/dev/null && prbsync auto

  show_python_prompt

  if [ "$ret" != "101" ] && [ "$ret" != "9" ] ; then
    echo "WARNING: Unable to use Python or QtPY. Falling back to xmessage" >&2
    xmessage \
    -title 'Windows' \
    -buttons Yes,No \
    'Reboot in order to boot into Windows?' 2> /dev/null
    ret=$?
  fi

  if [ "$ret" != "101" ]; then
    exit 1
  fi
fi

sudo /usr/bin/python3 -I /root/.local/bin/boot_windows
if [ "$?" != "0" ]; then
  exec ${SHELL:-sh}
fi
