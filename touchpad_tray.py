#!/usr/bin/env python3
import os
import signal
import subprocess
import threading
import time

LOCKFILE = "/tmp/touchpad_tray.lock"

def enforce_single_instance():
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"[+] Killed existing touchpad_tray instance (PID {pid})")
        except Exception as e:
            print(f"[!] Failed to kill existing instance: {e}")
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))

enforce_single_instance()

import gi
# Specify the versions **before** importing the modules, otherwise Gtk 4 may be
# auto‑loaded by other software and conflict with AppIndicator bindings.
gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk, AppIndicator3, GLib

APP_ID = "touchpad_tray"
SCHEMA = "org.gnome.desktop.peripherals.touchpad"
KEY = "send-events"
CONFIG_PATH = os.path.expanduser("~/.config/touchpad_tray.conf")

ICON_ENABLED = "input-touchpad-symbolic"
ICON_DISABLED = "input-mouse-symbolic"

def get_status():
    """Return the current touchpad send‑events state (enabled/disabled)."""
    try:
        result = subprocess.check_output(["gsettings", "get", SCHEMA, KEY])
        return result.strip().decode().strip("'")
    except Exception:
        return "unknown"


def set_status(enabled: bool):
    """Enable or disable the touchpad via gsettings."""
    value = "enabled" if enabled else "disabled"
    subprocess.call(["gsettings", "set", SCHEMA, KEY, value])


def is_mouse_connected():
    try:
        with open("/proc/bus/input/devices", "r") as f:
            blocks = f.read().lower().split("\n\n")
            for block in blocks:
                has_mouse = "handlers=" in block and "mouse" in block
                has_touchpad = "touchpad" in block

                # Skip internal touchpad devices masquerading as mice
                if has_mouse and not has_touchpad:
                    name_line = next((line for line in block.splitlines() if line.startswith("n: name=")), "")
                    name = name_line.split('"')[1] if '"' in name_line else ""

                    # Skip if same device exposes both mouse+touchpad (e.g. precision touchpad)
                    if "pnp0c50" in name or "touchpad" in name:
                        continue

                    return True
        return False
    except Exception as e:
        print(f"[!] Mouse detection error: {e}")
        return False


def load_config() -> bool:
    """Return True if auto‑disable feature should be active (default True)."""
    if not os.path.exists(CONFIG_PATH):
        return True  # default on first run
    try:
        with open(CONFIG_PATH, "r") as f:
            for line in f:
                if line.strip().startswith("auto_disable="):
                    return line.strip().split("=")[1] == "1"
    except Exception:
        pass
    return True


def save_config(enabled: bool):
    """Persist the auto‑disable preference."""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        if enabled:
            with open(CONFIG_PATH, "w") as f:
                f.write("auto_disable=1\n")
        else:
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
    except Exception:
        pass


class TouchpadTray:
    def __init__(self):
        self.auto_disable_enabled = load_config()
        self.monitor_thread = None

        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            ICON_ENABLED,
            AppIndicator3.IndicatorCategory.HARDWARE,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Build menu
        self.menu = Gtk.Menu()

        # Manual toggle
        self.toggle_item = Gtk.MenuItem(label="Toggle Touchpad")
        self.toggle_item.connect("activate", self.toggle_touchpad)
        self.menu.append(self.toggle_item)

        # Auto‑disable option
        self.auto_disable_item = Gtk.CheckMenuItem()
        self.update_auto_disable_label()
        self.auto_disable_item.set_active(self.auto_disable_enabled)
        self.auto_disable_item.connect("toggled", self.toggle_auto_disable)
        self.menu.append(self.auto_disable_item)

        # Quit
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        # Initial icon + periodic refresh
        self.update_icon()
        GLib.timeout_add_seconds(5, self.update_icon)

        if self.auto_disable_enabled:
            self.start_monitoring()

    # ───────────────────────── Menu callbacks ──────────────────────────
    def toggle_touchpad(self, _):
        current = get_status()
        set_status(current != "enabled")
        self.update_icon()
        
    def update_auto_disable_label(self):
        label = "Auto-disable if USB mouse connected "
        label += "✅ Enabled" if self.auto_disable_enabled else "❌ Disabled"
        self.auto_disable_item.set_label(label)
        self.auto_disable_item.set_active(self.auto_disable_enabled)

    def toggle_auto_disable(self, widget):
        self.auto_disable_enabled = widget.get_active()
        save_config(self.auto_disable_enabled)
        self.update_auto_disable_label()
        if self.auto_disable_enabled:
            self.start_monitoring()

    def quit(self, _):
        set_status(True)  # Ensure touchpad is enabled before exiting
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
        Gtk.main_quit()

    # ───────────────────────── Utility helpers ─────────────────────────
    def update_icon(self):
        status = get_status()
        if status == "enabled":
            self.indicator.set_icon_full(ICON_ENABLED, "Touchpad Enabled")
        elif status == "disabled":
            self.indicator.set_icon_full(ICON_DISABLED, "Touchpad Disabled")
        else:
            self.indicator.set_icon_full(ICON_DISABLED, "Touchpad Unknown")
        return True  # continue GLib timeout

    # ───────────────────────── Mouse monitor thread ────────────────────
    def start_monitoring(self):
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()

    def monitor_mouse(self):
        last_connected = None
        while self.auto_disable_enabled:
            connected = is_mouse_connected()
            if connected != last_connected:
                # Disable touchpad when mouse present; enable when absent
                set_status(not connected)
                GLib.idle_add(self.update_icon)
                last_connected = connected
            time.sleep(5)


if __name__ == "__main__":
    TouchpadTray()
    Gtk.main()

