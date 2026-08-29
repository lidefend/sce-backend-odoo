#!/bin/bash
cd /home/lidefend/workspace/sce-backend-odoo/frontend/apps/web
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
pnpm dev --host 127.0.0.1 --port 5175 --strictPort
