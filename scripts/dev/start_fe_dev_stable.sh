#!/bin/bash
# 稳定启动前端开发服务器
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
export PATH="/home/lidefend/.nvm/versions/node/v24.16.0/bin:$PATH"

cd /home/lidefend/workspace/sce-backend-odoo/frontend/apps/web

# 直接用 node 执行 vite.js，避免 pnpm_exec.sh 的间接调用问题
exec node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5175 --strictPort
