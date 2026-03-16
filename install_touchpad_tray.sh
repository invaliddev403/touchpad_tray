#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAY_SCRIPT_NAME="touchpad_tray.py"
RESET_SCRIPT_NAME="usb_reset_on_lid.py"
DESKTOP_FILE_NAME="touchpad-tray.desktop"
SERVICE_NAME="usb-reset-on-lid.service"

USER_INSTALL_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications"
SYSTEM_RESET_SCRIPT_PATH="/usr/local/bin/$RESET_SCRIPT_NAME"
SYSTEM_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
ICON_NAME="input-touchpad-symbolic"

INSTALL_RESET=""

usage() {
  cat <<EOF
Usage: $0 [--with-usb-reset|--without-usb-reset]

Installs the tray app and optionally the lid-open USB reset service.
If no option is provided, the script asks interactively.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-usb-reset)
      INSTALL_RESET="yes"
      ;;
    --without-usb-reset)
      INSTALL_RESET="no"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[!] Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

ensure_dependencies() {
  echo "[*] Ensuring dependencies are installed..."

  if command -v apt &>/dev/null; then
    sudo apt update
    sudo apt install -y \
      python3-gi \
      gir1.2-gtk-3.0 \
      gir1.2-ayatanaappindicator3-0.1 || \
    sudo apt install -y \
      gir1.2-appindicator3-0.1

    sudo apt install -y gsettings-desktop-schemas
    sudo apt install -y python3-evdev python3-pyudev libinput-tools xinput
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
Please install: Python GTK (PyGObject), Ayatana/AppIndicator3, python-evdev,
python-pyudev, libinput, and xinput manually.
EOF
    exit 1
  fi
}

ensure_input_group() {
  if ! id -nG "$USER" | tr ' ' '\n' | grep -q '^input$'; then
    echo "[*] Adding $USER to 'input' group (you'll need to log out/in once)"
    sudo gpasswd -a "$USER" input
  fi
}

install_tray() {
  local full_script_path="$USER_INSTALL_DIR/$TRAY_SCRIPT_NAME"

  echo "[*] Installing tray app..."
  mkdir -p "$USER_INSTALL_DIR" "$AUTOSTART_DIR" "$APPLICATIONS_DIR"
  install -m 0755 "$SCRIPT_DIR/$TRAY_SCRIPT_NAME" "$full_script_path"

  cat > "$AUTOSTART_DIR/$DESKTOP_FILE_NAME" <<EOF
[Desktop Entry]
Type=Application
Name=Touchpad Tray
Comment=Toggle touchpad from system tray (Wayland & X11) with auto-disable on USB/BT mouse
Exec=/usr/bin/env python3 $full_script_path
Icon=$ICON_NAME
Terminal=false
X-GNOME-Autostart-enabled=true
Categories=Utility;
EOF

  cp "$AUTOSTART_DIR/$DESKTOP_FILE_NAME" "$APPLICATIONS_DIR/$DESKTOP_FILE_NAME"

  echo "[✔] Installed tray script to: $full_script_path"
  echo "[✔] Autostart entry: $AUTOSTART_DIR/$DESKTOP_FILE_NAME"
  echo "[✔] App menu entry: $APPLICATIONS_DIR/$DESKTOP_FILE_NAME"
}

prompt_for_reset_install() {
  if [[ -n "$INSTALL_RESET" ]]; then
    return
  fi

  if [[ -t 0 ]]; then
    read -r -p "Install the optional lid-open USB reset service? [y/N] " reply
    case "$reply" in
      [yY]|[yY][eE][sS])
        INSTALL_RESET="yes"
        ;;
      *)
        INSTALL_RESET="no"
        ;;
    esac
  else
    INSTALL_RESET="no"
  fi
}

install_reset_service() {
  echo "[*] Installing optional lid-open USB reset service..."
  sudo install -m 0755 "$SCRIPT_DIR/$RESET_SCRIPT_NAME" "$SYSTEM_RESET_SCRIPT_PATH"
  sudo install -m 0644 "$SCRIPT_DIR/$SERVICE_NAME" "$SYSTEM_SERVICE_PATH"
  sudo systemctl daemon-reload
  sudo systemctl enable "$SERVICE_NAME"
  sudo systemctl restart "$SERVICE_NAME"

  echo "[✔] Installed reset script to: $SYSTEM_RESET_SCRIPT_PATH"
  echo "[✔] Enabled and restarted: $SERVICE_NAME"
}

ensure_dependencies
ensure_input_group
install_tray
prompt_for_reset_install

if [[ "$INSTALL_RESET" == "yes" ]]; then
  install_reset_service
else
  echo "[*] Skipping optional lid-open USB reset service."
fi

echo "[→] Log out/in once so the 'input' group membership applies."
