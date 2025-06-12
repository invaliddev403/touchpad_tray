# Description

This is a simple Touchpad Tray Icon for Wayland systems that will toggle the touchpad between enabled/disabled.

# Installer Script

```
chmod +x install_touchpad_tray.sh
.\install_touchpad_tray.sh
```

# Manual Install

## Install Requirements

```
sudo apt install \
  python3-gi \
  gir1.2-gtk-3.0 \
  gir1.2-appindicator3-0.1 \
  gsettings-desktop-schemas
```

## Enable Autostart

Update the .desktop file with the correct Exec path and place it at the following location:

```
~/.config/autostart/touchpad-tray.desktop
```

## Make Executable

```
chmod +x touchpad_tray.py
```
