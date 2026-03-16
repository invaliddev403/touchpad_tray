# Touchpad Tray (Universal - Wayland & X11)

[![Wayland](https://img.shields.io/badge/Wayland-supported-brightgreen)](#-how-it-works)
[![X11](https://img.shields.io/badge/X11-supported-brightgreen)](#-how-it-works)
[![Auto‑disable](https://img.shields.io/badge/Auto--disable-USB%2FBT%20mouse-blue)](#-auto-disable-policy)
[![Tray](https://img.shields.io/badge/System%20Tray-GTK%2FAyatana-9cf)](#-installation-using-installer-script)

A simple tray utility that **enables/disables the touchpad** automatically depending on whether an **external (USB/Bluetooth) mouse** is connected. Works on **Wayland** (COSMIC, GNOME, etc.) and **X11**.

> On some Wayland desktops the GNOME `gsettings` key isn’t honored; this app controls the device directly:
> - **Wayland:** via *evdev* grab/ungrab (user in `input` group, no sudo at runtime).
> - **X11:** via `xinput` (with evdev as fallback).

---

## Features

- Works on **Wayland** and **X11** automatically.
- **Auto‑disable policy** (always on):  
  1. No external USB/BT mouse → **Touchpad Enabled**  
  2. External USB/BT mouse connected → **Touchpad Disabled**  
  3. External mouse disconnected → **Touchpad Enabled**  
- **Manual toggle** acts as a temporary override (toggle again to return to auto).
- **Debug menu:** “List external‑mouse devices” to show what the app is counting.
- Autostart support + app menu entry.
- Optional lid-open USB reset service for external mice that need a reset after resume.

---

## Installation (using installer script)

```bash
chmod +x install_touchpad_tray.sh
./install_touchpad_tray.sh
```

The script will:

- Install the script to `~/.local/bin`.
- Create autostart and applications menu entries.
- Install required dependencies: `python3-gi`, `gir1.2-gtk-3.0`, **Ayatana/AppIndicator**, `python3-evdev`, **python3-pyudev**, `libinput-tools`, `xinput`.
- Add your user to the `input` group (log out/in once).
- Ask whether to install the optional `usb-reset-on-lid.service`.

If you want to skip or force the reset service without a prompt:

```bash
./install_touchpad_tray.sh --without-usb-reset
./install_touchpad_tray.sh --with-usb-reset
```

The optional reset service installs:

- [usb_reset_on_lid.py](/home/juniper/Tools/touchpad_tray/usb_reset_on_lid.py) to `/usr/local/bin/usb_reset_on_lid.py`
- [usb-reset-on-lid.service](/home/juniper/Tools/touchpad_tray/usb-reset-on-lid.service) to `/etc/systemd/system/usb-reset-on-lid.service`

---

## Manual Install

**Debian / Ubuntu / Pop!\_OS**

```bash
sudo apt update
sudo apt install \
  python3-gi \
  gir1.2-gtk-3.0 \
  gir1.2-ayatanaappindicator3-0.1 \
  gsettings-desktop-schemas \
  python3-evdev \
  python3-pyudev \
  libinput-tools \
  xinput
sudo gpasswd -a "$USER" input   # log out/in after this
```

**Arch Linux**

```bash
sudo pacman -S \
  python-gobject \
  libappindicator-gtk3 \
  gsettings-desktop-schemas \
  python-evdev \
  python-pyudev \
  libinput \
  xorg-xinput
sudo gpasswd -a "$USER" input
```

**Install the script and desktop files**

```bash
mkdir -p ~/.local/bin ~/.config/autostart ~/.local/share/applications
cp touchpad_tray.py ~/.local/bin/
chmod +x ~/.local/bin/touchpad_tray.py
sed "s|Exec=.*|Exec=/usr/bin/env python3 $HOME/.local/bin/touchpad_tray.py|" \
  touchpad-tray.desktop > ~/.config/autostart/touchpad-tray.desktop
cp ~/.config/autostart/touchpad-tray.desktop \
   ~/.local/share/applications/touchpad-tray.desktop
```

Run it manually for a first launch:

```bash
python3 ~/.local/bin/touchpad_tray.py &
```

---

## How detection works

- We listen to **udev** events on `SUBSYSTEM=input` and treat a device as **external mouse** iff:
  - `ID_INPUT_MOUSE=1` **and** (`ID_BUS=usb` or `bluetooth`, or the device path contains `/usb/` or `/bluetooth/`), and
  - It is **not** a touchpad (`ID_INPUT_TOUCHPAD!=1`) and **not** an internal i2c/serio/platform device (heuristics exclude common names like Synaptics/ELAN and i2c/serio paths).
- We also keep a light **periodic poll** and fall back to `libinput`/`/proc/bus/input/devices` if needed.

This avoids misclassifying internal touchpads that also expose a “mouse” node.

---

## Troubleshooting

| Symptom | What to check |
|---|---|
| Touchpad won’t disable/enable on Wayland | Confirm group membership: `groups | grep -w input` (then log out/in if you just added it) |
| Auto‑disable not reacting to USB receiver | `udevadm monitor --udev --property` should show `SUBSYSTEM=input` events with `ID_INPUT_MOUSE=1` on plug/unplug |
| AppIndicator tray icon missing | Install Ayatana: `gir1.2-ayatanaappindicator3-0.1` (Pop!\_OS/Ubuntu) |
| X11 toggling doesn’t work | Install `xinput` and ensure `$XDG_SESSION_TYPE` is `x11` |
| See what the app counts as “external” | Tray → **Debug: List external‑mouse devices** |

---

## Uninstall

```bash
rm -f ~/.local/bin/touchpad_tray.py
rm -f ~/.config/autostart/touchpad-tray.desktop
rm -f ~/.local/share/applications/touchpad-tray.desktop
sudo gpasswd -d "$USER" input
```

If you installed the optional lid-reset service:

```bash
sudo systemctl disable --now usb-reset-on-lid.service
sudo rm -f /etc/systemd/system/usb-reset-on-lid.service
sudo rm -f /usr/local/bin/usb_reset_on_lid.py
sudo systemctl daemon-reload
```

---

## Notes

- Do **not** run with `sudo` — it must run inside your user’s GUI session.
- On exit the app attempts to **re‑enable** the touchpad so you’re never stranded.

---

## License
MIT
