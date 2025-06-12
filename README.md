This is a simple Touchpad Tray Icon for Wayland systems that will toggle the touchpad between enabled/disabled.

# Requirements

```
sudo apt install \
  python3-gi \
  gir1.2-gtk-3.0 \
  gir1.2-appindicator3-0.1 \
  gsettings-desktop-schemas
```

# Autostart

Update the .desktop file with the correct Exec path and place it at the following location:

```
~/.config/autostart/touchpad-tray.desktop
```
