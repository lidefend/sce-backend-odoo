import subprocess
import os
import time

os.chdir('/home/lidefend/workspace/sce-backend-odoo/frontend/apps/web')
env = os.environ.copy()
env['NVM_DIR'] = os.path.expanduser('~/.nvm')
nvm_sh = os.path.join(env['NVM_DIR'], 'nvm.sh')

# Source nvm and run pnpm
cmd = f'source {nvm_sh} && pnpm dev --host 127.0.0.1 --port 5175 --strictPort'
with open('/tmp/vite-dev.log', 'w') as f:
    proc = subprocess.Popen(['bash', '-c', cmd], stdout=f, stderr=subprocess.STDOUT, env=env, cwd=os.getcwd())

print(f'Vite PID: {proc.pid}')
time.sleep(12)

# Check if port is listening
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('127.0.0.1', 5175))
sock.close()
print(f'Port 5175 listening: {result == 0}')

# Read log
with open('/tmp/vite-dev.log', 'r') as f:
    print('--- Log ---')
    print(f.read()[-500:])
