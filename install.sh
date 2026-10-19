#!/usr/bin/env bash
# PaperclipLite Installer (Raspberry Pi / Debian / Ubuntu / MX Linux)
#   ./install.sh            -> venv + Abhaengigkeiten + .env mit zufaelligem Passwort
#   ./install.sh --service  -> zusaetzlich systemd-Dienst einrichten und starten (braucht sudo)
#   ./install.sh --piper    -> zusaetzlich Piper (gute deutsche Offline-Stimme) einrichten; beides kombinierbar
#   Danach pruefen:  ./venv/bin/python selftest.py
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"

command -v python3 >/dev/null || { echo "python3 fehlt: sudo apt install python3 python3-venv"; exit 1; }
[ -d venv ] || python3 -m venv venv || { echo "Tipp: sudo apt install python3-venv"; exit 1; }
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
echo "Abhaengigkeiten installiert."
# Systemprogramme fuer Video/Sprache/Schriften (optional, aber noetig fuer Medien-Agenten)
MISSING=""
command -v ffmpeg >/dev/null || MISSING="$MISSING ffmpeg"
command -v espeak-ng >/dev/null || MISSING="$MISSING espeak-ng"
command -v tesseract >/dev/null || MISSING="$MISSING tesseract-ocr tesseract-ocr-deu poppler-utils"
command -v tesseract >/dev/null && ! tesseract --list-langs 2>/dev/null | grep -qx deu && MISSING="$MISSING tesseract-ocr-deu"
command -v pdftoppm >/dev/null || case "$MISSING" in *poppler-utils*) ;; *) MISSING="$MISSING poppler-utils";; esac
fc-list 2>/dev/null | grep -qi dejavu || MISSING="$MISSING fonts-dejavu-core"
if [ -n "$MISSING" ]; then
  echo "Fuer Video, Sprache, OCR (gescannte PDFs) und Sonderzeichen in PDFs empfohlen:  sudo apt install$MISSING"
fi

# Piper: gute Offline-Stimme (deutsch). Optional:  ./install.sh --piper
if [ "${1:-}" = "--piper" ] || [ "${2:-}" = "--piper" ]; then
  echo "Piper-Sprachausgabe wird eingerichtet (ca. 100 MB) ..."
  ./venv/bin/pip install -q piper-tts
  mkdir -p models/piper
  ./venv/bin/python -m piper.download_voices de_DE-thorsten-medium --download-dir models/piper \
    && echo "Piper fertig: Stimme in models/piper/ (wird automatisch genutzt)." \
    || echo "Stimme konnte nicht geladen werden (Internet?). Erneut versuchen: ./install.sh --piper"
fi

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

if [ "${1:-}" = "--service" ] || [ "${2:-}" = "--service" ]; then
  sed -e "s|__USER__|$(id -un)|g" -e "s|__DIR__|${DIR}|g" -e "s|__HOME__|${HOME}|g" deploy/paperclip-lite.service \
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
