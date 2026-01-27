import sys, time

last = ''
while True:
  now = time.strftime('%I : %M : %S %p  ')
  sys.stdout.write(('\b'*len(last)) + (' '*len(last)) + ('\b'*len(last)))
  sys.stdout.write(now)
  sys.stdout.flush()
  last = now
  time.sleep(0.5)
