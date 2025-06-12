#!/bin/bash

set -e

SCRIPT_NAME="touchpad_tray.py"
DESKTOP_FILE_NAME="touchpad-tray.desktop"
INSTALL_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
ICON_NAME="input-touchpad-symbolic"  # You can change this to a path if needed

echo "[*] Ensuring dependencies are installed..."

# Try apt or pacman depending on distro
if command -v apt &>/dev/null; then
    sudo apt update
    sudo apt install -y \
        python3-gi \
        gir1.2-gtk-3.0 \
        gir1.2-appindicator3-0.1 \
        gsettings-desktop-schemas
elif command -v pacman &>/dev/null; then
    sudo pacman -Sy --noconfirm \
        python-gobject \
        libappindicator-gtk3 \
        gsettings-desktop-schemas
else
    echo "[!] Unsupported package manager. Please install Python GTK and AppIndicator bindings manually."
    exit 1
fi

echo "[*] Installing script..."

mkdir -p "$INSTALL_DIR"
chmod +x "$SCRIPT_NAME"
cp "$SCRIPT_NAME" "$INSTALL_DIR/"

FULL_SCRIPT_PATH="$INSTALL_DIR/$SCRIPT_NAME"

echo "[*] Creating autostart desktop file..."

mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/$DESKTOP_FILE_NAME" <<EOF
[Desktop Entry]
Type=Application
Exec=$FULL_SCRIPT_PATH
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Touchpad Tray
Comment=Toggle touchpad from system tray (Wayland-safe)
Icon=$ICON_NAME
Terminal=false
EOF

echo "[✔] Installed to: $FULL_SCRIPT_PATH"
echo "[✔] Autostart entry created: $AUTOSTART_DIR/$DESKTOP_FILE_NAME"
echo "[→] You can now run the tray app manually or reboot to auto-start it."

