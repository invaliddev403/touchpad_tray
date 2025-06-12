#!/usr/bin/env python3
import gi
import subprocess
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib

APP_ID = "touchpad_tray"
SCHEMA = "org.gnome.desktop.peripherals.touchpad"
KEY = "send-events"

# Icons (must exist in icon theme or path)
ICON_ENABLED = "input-touchpad-symbolic"
ICON_DISABLED = "input-mouse-symbolic"

def get_status():
    try:
        result = subprocess.check_output(["gsettings", "get", SCHEMA, KEY])
        return result.strip().decode().strip("'")
    except:
        return "unknown"

def set_status(enabled):
    value = 'enabled' if enabled else 'disabled'
    subprocess.call(["gsettings", "set", SCHEMA, KEY, value])

class TouchpadTray:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            APP_ID,
            ICON_ENABLED,
            AppIndicator3.IndicatorCategory.HARDWARE
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.menu = Gtk.Menu()

        self.toggle_item = Gtk.MenuItem(label="Toggle Touchpad")
        self.toggle_item.connect("activate", self.toggle_touchpad)
        self.menu.append(self.toggle_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        self.update_icon()  # ← show correct icon on start

        # Optional: refresh icon every 5 seconds (in case external toggle used)
        GLib.timeout_add_seconds(5, self.update_icon)

    def toggle_touchpad(self, _):
        current = get_status()
        if current == "enabled":
            set_status(False)
        else:
            set_status(True)
        self.update_icon()

    def update_icon(self):
        status = get_status()
        if status == "enabled":
            #self.indicator.set_icon(ICON_ENABLED)
            self.indicator.set_icon_full(ICON_ENABLED, "Touchpad Enabled")
        elif status == "disabled":
            #self.indicator.set_icon(ICON_DISABLED)
            self.indicator.set_icon_full(ICON_DISABLED, "Touchpad Disabled")
        else:
            #self.indicator.set_icon(ICON_DISABLED)
            self.indicator.set_icon_full(ICON_DISABLED, "Touchpad Disabled")
        return True  # needed for GLib timeout to repeat

    def quit(self, _):
        Gtk.main_quit()

if __name__ == "__main__":
    TouchpadTray()
    Gtk.main()

