# Description

This is a simple Touchpad Tray Icon for Wayland systems that will toggle the touchpad between enabled/disabled.

It also includes an **auto-disable feature** that disables the touchpad when an external USB or Bluetooth mouse is detected (similar to Windows 11). This behavior is enabled by default and can be toggled via the tray icon menu.

# Installer Script

```bash
chmod +x install_touchpad_tray.sh
./install_touchpad_tray.sh
```

# Manual Install

## Install Requirements

```bash
sudo apt install \
  python3-gi \
  gir1.2-gtk-3.0 \
  gir1.2-appindicator3-0.1 \
  gsettings-desktop-schemas \
  usbutils
```

## Enable Autostart

Update the `.desktop` file with the correct `Exec` path and place it at the following location:

```bash
~/.config/autostart/touchpad-tray.desktop
```

## Make Executable

```bash
chmod +x touchpad_tray.py
```

## Optional Configuration

Auto-disable is **enabled by default**. You can toggle this at runtime via the tray menu.

Config is stored in:
```bash
~/.config/touchpad_tray.conf
```
Delete this file to reset to defaults.

