#!/bin/bash
# Removes Snipping Tool.
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo)."
  exit 1
fi
/usr/bin/python3 "$SRC/keybind.py" --remove
pkill -HUP -u "$USER" -x labwc 2>/dev/null || true

sudo rm -rf /opt/pi-snip /usr/local/bin/pi-snip /usr/share/applications/pi-snip.desktop \
  /usr/share/icons/hicolor/scalable/apps/pi-snip.svg
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "Snipping Tool removed. Your settings are still in ~/.config/pi-snip (delete that folder to remove them)."
