# Must use kernel args console=ttyS0,9600 log_buf_len=2147483648

import subprocess, shlex, threading, time

fh = open('/var/tmp/stacks_at_shutdown.log', 'ab')

circ = {}

p = subprocess.Popen(shlex.split('qemu-system-x86_64 -machine type=q35,accel=kvm -m 16G -serial mon:stdio -vga virtio -drive file=/var/tmp/linux_vm.img,if=virtio -smp 30 -drive if=pflash,format=raw,file=/usr/share/edk2/x64/OVMF.fd -netdev user,id=net0,hostfwd=tcp::6022-:22,hostfwd=tcp::6080-:80 -device virtio-net-pci,netdev=net0'), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def worker():
  while True:
    buf = p.stdout.read(1)
    if not buf:
      return
    fh.write(buf)
    circ['v'] = (circ.get('v',b'') + buf)[-99999:]

def wait_and_input(wait_for, inp):
  print(f'Waiting for "{wait_for}"')
  while wait_for.encode() not in circ.get('v',b''):
    time.sleep(1)
  p.stdin.write(inp.encode())
  p.stdin.flush()
  circ['v'] = b''
  print(f'Sent "{repr(inp)}"')

t = threading.Thread(target=worker)
t.start()

wait_and_input('login:', 'root\n')
wait_and_input('Password:', '1\n')
wait_and_input(']#', '/root/hack.sh\n')
wait_and_input('login:', 'root\n')
wait_and_input('Password:', '1\n')
wait_and_input(']#', 'echo "7" > /proc/sys/kernel/printk\n')
wait_and_input(']#', 'poweroff\n')

p.wait()
