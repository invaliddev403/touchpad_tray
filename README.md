# Description

This is a simple Touchpad Tray Icon for Wayland systems that will toggle the touchpad between enabled/disabled.

It also includes an **auto-disable feature** that disables the touchpad when an external USB or Bluetooth mouse is detected (similar to Windows 11). This behavior is enabled by default and can be toggled via the tray icon menu.

# Installer Script

```bash
chmod +x install_touchpad_tray.sh
./install_touchpad_tray.sh
```

This will:
- Install the tray app to `~/.local/bin`
- Create an autostart entry in `~/.config/autostart`
- Add a launcher icon to your desktop app menu via `~/.local/share/applications`
- Install all required dependencies using either `apt` or `pacman`

# Manual Install

## Install Requirements

```bash
# Debian/Ubuntu
sudo apt install \
  python3-gi \
  gir1.2-gtk-3.0 \
  gir1.2-appindicator3-0.1 \
  gsettings-desktop-schemas \
  usbutils

# Arch
sudo pacman -S \
  python-gobject \
  libappindicator-gtk3 \
  gsettings-desktop-schemas
```

## Install Script Manually

1. Copy the script into your PATH:
```bash
mkdir -p ~/.local/bin
cp touchpad_tray.py ~/.local/bin/
chmod +x ~/.local/bin/touchpad_tray.py
```

2. Install the `.desktop` file:
```bash
mkdir -p ~/.config/autostart ~/.local/share/applications

# Update Exec path and install to both locations
sed "s|Exec=.*|Exec=$HOME/.local/bin/touchpad_tray.py|" touchpad-tray.desktop > ~/.config/autostart/touchpad-tray.desktop
cp ~/.config/autostart/touchpad-tray.desktop ~/.local/share/applications/touchpad-tray.desktop
```

✅ This ensures:
- The app autostarts on login
- The app appears in your desktop launcher (Activities, Start menu, etc)

## Optional Configuration

Auto-disable is **enabled by default**. You can toggle this at runtime via the tray menu.

Config is stored in:
```bash
~/.config/touchpad_tray.conf
```
Delete this file to reset to defaults.

