#!/usr/bin/env bash
# PaperclipLite Installer (Raspberry Pi / Debian / Ubuntu / MX Linux)
#   ./install.sh            -> venv + Abhaengigkeiten + .env mit zufaelligem Passwort
#   ./install.sh --service  -> zusaetzlich systemd-Dienst einrichten und starten (braucht sudo)
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"

command -v python3 >/dev/null || { echo "python3 fehlt: sudo apt install python3 python3-venv"; exit 1; }
[ -d venv ] || python3 -m venv venv || { echo "Tipp: sudo apt install python3-venv"; exit 1; }
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
echo "Abhaengigkeiten installiert."

if [ ! -f .env ]; then
  cp .env.example .env
  PW="$(./venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(18))')"
  sed -i "s|^APP_TOKEN=.*|APP_TOKEN=${PW}|" .env
  chmod 600 .env
  echo
  echo "============================================================"
  echo " .env angelegt. Dein Login-Passwort (jetzt notieren):"
  echo "   ${PW}"
  echo " API-Keys eintragen:  nano .env"
  echo "============================================================"
else
  echo ".env existiert bereits - unveraendert gelassen."
fi

if [ "${1:-}" = "--service" ]; then
  sed -e "s|__USER__|$(id -un)|g" -e "s|__DIR__|${DIR}|g" deploy/paperclip-lite.service \
    | sudo tee /etc/systemd/system/paperclip-lite.service >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable --now paperclip-lite
  sleep 2
  systemctl --no-pager --lines=5 status paperclip-lite || true
  echo "Dienst laeuft. Logs: journalctl -u paperclip-lite -f"
else
  echo
  echo "Manuell starten:   ./venv/bin/python app.py     (http://127.0.0.1:8787)"
  echo "Als Dienst:        ./install.sh --service"
fi
