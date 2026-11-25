#!/bin/bash
# Installer for Snipping Tool (Windows 11 style) on Raspberry Pi
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo). It will ask for sudo when needed."
  exit 1
fi

echo "==> Installing packages"
sudo apt-get update
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 grim xdg-utils
sudo apt-get install -y fonts-open-sans || echo "   (Open Sans font not available, using system font)"
for p in wl-clipboard; do
  sudo apt-get install -y "$p" || echo "   ($p not available, skipping)"
done

echo "==> Installing app"
sudo install -d /opt/pi-snip
sudo install -m 644 "$SRC/pi_snip.py" /opt/pi-snip/pi_snip.py
printf '#!/bin/sh\nexec /usr/bin/python3 /opt/pi-snip/pi_snip.py "$@"\n' | sudo tee /usr/local/bin/pi-snip >/dev/null
sudo chmod 755 /usr/local/bin/pi-snip

echo "==> Adding menu entry and icon"
sudo install -D -m 644 "$SRC/pi-snip.svg" /usr/share/icons/hicolor/scalable/apps/pi-snip.svg
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
sudo tee /usr/share/applications/pi-snip.desktop >/dev/null <<'DESK'
[Desktop Entry]
Type=Application
Name=Snipping Tool
GenericName=Screenshot Tool
Comment=Take and mark up screenshots
Exec=pi-snip 
Icon=pi-snip
Terminal=false
Categories=Utility;Graphics;GTK;
StartupWMClass=pi-snip
StartupNotify=true
DESK
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true

echo "==> Adding Super+Shift+S shortcut"
/usr/bin/python3 "$SRC/keybind.py"
pkill -HUP -u "$USER" -x labwc 2>/dev/null || true
mkdir -p "$HOME/Pictures/Screenshots"

echo
echo "Done. Open Snipping Tool from the menu or run: pi-snip"
