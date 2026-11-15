#!/data/data/com.termux/files/usr/bin/bash
# Arranca el puente de TikTok Live en Termux.
# Uso:  bash iniciar.sh            (el @usuario lo pones en la app, en ⚙️)
#       bash iniciar.sh tuusuario  (o directo desde aquí)
cd "$(dirname "$0")" || exit 1
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock
if [ ! -d node_modules ]; then
  echo "Instalando dependencias (solo la primera vez)..."
  npm install || exit 1
fi
node server.js "$@"
