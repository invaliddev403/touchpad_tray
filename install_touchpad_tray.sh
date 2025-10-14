#!/bin/bash
set -euo pipefail

SCRIPT_NAME="touchpad_tray.py"
DESKTOP_FILE_NAME="touchpad-tray.desktop"
INSTALL_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications"
ICON_NAME="input-touchpad-symbolic"  # or a path to your own icon

echo "[*] Ensuring dependencies are installed..."

if command -v apt &>/dev/null; then
  sudo apt update
  # Core GTK + AppIndicator (prefer Ayatana, fallback to AppIndicator3)
  sudo apt install -y \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-ayatanaappindicator3-0.1 || \
  sudo apt install -y \
    gir1.2-appindicator3-0.1

  # GNOME schemas (for gsettings reads/writes if DE honors it)
  sudo apt install -y gsettings-desktop-schemas

  # Backends + tooling
  sudo apt install -y python3-evdev python3-pyudev libinput-tools xinput

  # Optional diagnostics
  sudo apt install -y usbutils inotify-tools || true

elif command -v pacman &>/dev/null; then
  sudo pacman -Sy --noconfirm \
    python-gobject \
    libappindicator-gtk3 \
    gsettings-desktop-schemas \
    python-evdev \
    python-pyudev \
    libinput \
    xorg-xinput \
    inotify-tools
else
  cat >&2 <<EOF
[!] Unsupported package manager.
Please install: Python GTK (PyGObject), Ayatana/AppIndicator3, python-evdev, python-pyudev, libinput, and xinput manually.
EOF
  exit 1
fi

# Add user to 'input' so evdev grab works on Wayland
if ! id -nG "$USER" | tr ' ' '\n' | grep -q '^input$'; then
  echo "[*] Adding $USER to 'input' group (you'll need to log out/in once)"
  sudo gpasswd -a "$USER" input
fi

echo "[*] Installing script..."
mkdir -p "$INSTALL_DIR"
install -m 0755 "$SCRIPT_NAME" "$INSTALL_DIR/"

FULL_SCRIPT_PATH="$INSTALL_DIR/$SCRIPT_NAME"

echo "[*] Creating desktop entries..."
mkdir -p "$AUTOSTART_DIR" "$APPLICATIONS_DIR"

cat > "$AUTOSTART_DIR/$DESKTOP_FILE_NAME" <<EOF
[Desktop Entry]
Type=Application
Name=Touchpad Tray
Comment=Toggle touchpad from system tray (Wayland & X11) with auto-disable on USB/BT mouse
Exec=/usr/bin/env python3 $FULL_SCRIPT_PATH
Icon=$ICON_NAME
Terminal=false
X-GNOME-Autostart-enabled=true
Categories=Utility;
EOF

# Also install into the user's application menu
cp "$AUTOSTART_DIR/$DESKTOP_FILE_NAME" "$APPLICATIONS_DIR/$DESKTOP_FILE_NAME"

echo "[✔] Installed to: $FULL_SCRIPT_PATH"
echo "[✔] Autostart entry: $AUTOSTART_DIR/$DESKTOP_FILE_NAME"
echo "[✔] App menu entry: $APPLICATIONS_DIR/$DESKTOP_FILE_NAME"
echo "[→] Log out/in once so the 'input' group membership applies."
