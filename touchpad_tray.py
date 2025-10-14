#!/usr/bin/env python3
import os, sys, time, subprocess, threading, getpass, re
import gi

# ---------- Guards ----------
if os.geteuid() == 0:
    print("[!] Do not run as root/sudo. Run in your user desktop session.")
    sys.exit(1)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

# AppIndicator ↔ Ayatana fallback
Indicator = None
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as AppInd
    Indicator = AppInd.Indicator
except Exception:
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppInd
        Indicator = AppInd.Indicator
    except Exception:
        AppInd = None

ok, _ = Gtk.init_check()
if not ok:
    print("[!] No GUI display available. Run from your logged-in desktop session.")
    sys.exit(1)

# ---------- Env / Paths ----------
APP_ID = "touchpad_tray"
ICON_ENABLED = "input-touchpad-symbolic"
ICON_DISABLED = "input-mouse-symbolic"

IS_WAYLAND = (os.environ.get("XDG_SESSION_TYPE") or "").lower() == "wayland"
DESKTOP = (os.environ.get("XDG_CURRENT_DESKTOP") or "").upper()

_runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
_fallback = os.path.expanduser(f"~/.cache/{getpass.getuser()}")
os.makedirs(_fallback, exist_ok=True)
LOCKDIR = _runtime if os.path.isdir(_runtime) and os.access(_runtime, os.W_OK) else _fallback
LOCKFILE = os.path.join(LOCKDIR, "touchpad_tray.lock")

def enforce_single_instance():
    try:
        fd = os.open(LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
    except FileExistsError:
        try:
            with open(LOCKFILE, "r") as f:
                pid = int((f.read() or "0").strip())
            os.kill(pid, 0)
            print(f"[!] Another instance is running (PID {pid}).")
            sys.exit(0)
        except Exception:
            try: os.remove(LOCKFILE)
            except Exception: pass
            return enforce_single_instance()
enforce_single_instance()

# ---------- Helpers ----------
def which(cmd: str) -> bool:
    return subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

# ---------- Backends: evdev + xinput ----------
# evdev (Wayland-safe; works on X11 too)
EVDEV_AVAILABLE = False
try:
    from evdev import InputDevice
    EVDEV_AVAILABLE = True
except Exception:
    pass

def _touchpad_event_via_libinput():
    if not which("libinput"): return None
    try:
        out = subprocess.check_output(["libinput", "list-devices"], text=True, stderr=subprocess.DEVNULL)
        dev, node, tags = None, None, ""
        def accept():
            return node and ("touchpad" in (dev or "").lower() or "touchpad" in (tags or ""))
        for line in out.splitlines() + [""]:
            if line.startswith("Device:"):
                if accept(): return node
                dev, node, tags = line[7:].strip(), None, ""
            elif "Kernel:" in line and "/dev/input/event" in line:
                node = line.split()[-1].strip()
            elif "Tags:" in line:
                tags = line.split(":",1)[1].strip().lower()
            elif not line.strip():
                if accept(): return node
    except Exception:
        pass
    return None

def _touchpad_event_via_proc():
    try:
        txt = open("/proc/bus/input/devices","r",encoding="utf-8",errors="ignore").read()
        for block in txt.split("\n\n"):
            low = block.lower()
            if "touchpad" in low and "handlers=" in low:
                for part in block.split():
                    if part.startswith("event"):
                        p = f"/dev/input/{part}"
                        if os.path.exists(p): return p
    except Exception:
        pass
    return None

def find_touchpad_event():
    node = _touchpad_event_via_libinput()
    if node: return node
    return _touchpad_event_via_proc()

class EvdevController:
    def __init__(self):
        self.event_path = None
        self.dev = None
        self.enabled = True
    def resolve(self):
        if not EVDEV_AVAILABLE:
            raise RuntimeError("python3-evdev not installed.")
        self.close()
        node = find_touchpad_event()
        if not node:
            raise RuntimeError("Touchpad event node not found. Install libinput-tools and retry.")
        self.event_path = node
        try:
            self.dev = InputDevice(self.event_path)
        except PermissionError:
            raise PermissionError(
                f"Permission denied opening {self.event_path}. "
                "Add your user to 'input' group then re-log: sudo gpasswd -a $USER input"
            )
    def set_enabled(self, enabled: bool) -> bool:
        if self.dev is None:
            self.resolve()
        if enabled:
            try: self.dev.ungrab()
            except Exception: pass
            self.enabled = True
            return True
        else:
            try:
                self.dev.grab()
                self.enabled = False
                return True
            except Exception:
                # hotplug → one re-resolve attempt
                self.resolve()
                self.dev.grab()
                self.enabled = False
                return True
    def get_status(self) -> str:
        return "enabled" if self.enabled else "disabled"
    def close(self):
        try:
            if self.dev:
                try: self.dev.ungrab()
                except Exception: pass
                try: self.dev.close()
                except Exception: pass
        finally:
            self.dev = None

# xinput (X11 only)
HAS_XINPUT = (not IS_WAYLAND) and which("xinput")

def xinput_touchpad_ids():
    ids = []
    if not HAS_XINPUT: return ids
    try:
        out = subprocess.check_output(["xinput","list"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if "id=" in line and any(k in line.lower() for k in ("touchpad","synaptics","elan","trackpad","libinput touchpad")):
                try:
                    dev_id = int(line.split("id=")[1].split()[0])
                    ids.append(dev_id)
                except Exception:
                    pass
    except Exception:
        pass
    return ids

def xinput_get_enabled(dev_id):
    try:
        out = subprocess.check_output(["xinput","list-props",str(dev_id)], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if "Device Enabled" in line:
                return line.split(":")[-1].strip() == "1"
    except Exception:
        pass
    return None

def xinput_set_enabled(dev_id, enabled):
    try:
        subprocess.check_call(["xinput","set-prop",str(dev_id),"Device Enabled","1" if enabled else "0"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

# Unified controller choosing best backend for current session
class UnifiedController:
    def __init__(self):
        self.ev = EvdevController() if EVDEV_AVAILABLE else None
        self.last_backend = None  # "xinput" or "evdev"
        # Pre-resolve evdev on Wayland, on X11 keep lazy
        if IS_WAYLAND and self.ev:
            try: self.ev.resolve()
            except Exception as e: print(f"[i] evdev note: {e}")
    def set_enabled(self, enabled: bool) -> bool:
        # Prefer X11 xinput on X11, else evdev
        if HAS_XINPUT:
            ids = xinput_touchpad_ids()
            if ids:
                ok = False
                for dev_id in ids:
                    ok |= xinput_set_enabled(dev_id, enabled)
                if ok:
                    self.last_backend = "xinput"
                    return True
        # evdev fallback / Wayland primary
        if self.ev:
            try:
                ok = self.ev.set_enabled(enabled)
                if ok:
                    self.last_backend = "evdev"
                    return True
            except Exception as e:
                print(f"[!] evdev toggle failed: {e}")
        return False
    def get_status(self) -> str:
        if HAS_XINPUT:
            ids = xinput_touchpad_ids()
            if ids:
                any_en = False; any_dis = False
                for dev_id in ids:
                    st = xinput_get_enabled(dev_id)
                    if st is True: any_en = True
                    if st is False: any_dis = True
                if any_dis and not any_en: return "disabled"
                if any_en: return "enabled"
        if self.ev:
            return self.ev.get_status()
        return "unknown"
    def info(self) -> str:
        return f"backend={self.last_backend or ('xinput' if HAS_XINPUT else 'evdev' if self.ev else 'none')} wayland={IS_WAYLAND}"

# ---------- External mouse presence detection ----------
UDEV_AVAILABLE = False
try:
    import pyudev
    UDEV_AVAILABLE = True
except Exception:
    pass

INTERNAL_NAME_HINTS = re.compile(r'(synaptics|syna\d|elan|dllk|i2c|pnp0c50|atmel|alps)', re.I)

def _is_external_mouse_dev(udev_dev) -> bool:
    """Return True if udev input device should be treated as an external mouse."""
    props = udev_dev.properties
    if props.get('ID_INPUT_MOUSE') != '1':
        return False
    if props.get('ID_INPUT_TOUCHPAD') == '1':
        return False
    # Consider buses: external if USB or Bluetooth
    bus = (props.get('ID_BUS') or '').lower()
    if bus in ('usb', 'bluetooth'):
        return True
    # Heuristics: DEVPATH containing /usb/ or bluetooth/
    path = (udev_dev.device_path or '')
    if '/usb' in path or '/bluetooth' in path:
        return True
    # Exclude internal i2c/serio platform devices by name/Path hints
    name = (props.get('NAME') or '').strip('"')
    id_path = (props.get('ID_PATH') or '').lower()
    phys = (props.get('PHYS') or '').lower()
    if INTERNAL_NAME_HINTS.search(name) and ('usb' not in id_path and 'bluetooth' not in id_path):
        return False
    if ('i2c-' in path or 'serio' in path or 'platform-' in path) and 'usb' not in path and 'bluetooth' not in path:
        return False
    # Default to False (conservative) if unsure
    return False

def enumerate_external_mice(ctx: "pyudev.Context"):
    out = []
    for d in ctx.list_devices(subsystem='input'):
        try:
            if _is_external_mouse_dev(d):
                out.append((d.device_node or d.device_path, d.properties.get('NAME')))
        except Exception:
            pass
    return out

def libinput_has_external_mouse():
    if not which("libinput"): return None
    try:
        out = subprocess.check_output(["libinput","list-devices"], text=True, stderr=subprocess.DEVNULL).splitlines()
    except Exception:
        return None
    has = False
    dev = None
    caps = ""
    for ln in out + [""]:
        if ln.startswith("Device:"):
            # evaluate previous block
            if dev and ("pointer" in caps.lower()) and ("touchpad" not in dev.lower()):
                has = True
            # start new
            dev = ln.split(":",1)[1].strip()
            caps = ""
        elif ln.startswith("Capabilities:"):
            caps = ln.split(":",1)[1].strip()
        elif not ln.strip():
            if dev and ("pointer" in caps.lower()) and ("touchpad" not in dev.lower()):
                has = True
            dev = None; caps = ""
    return has

def proc_has_external_mouse() -> bool:
    try:
        txt = open("/proc/bus/input/devices","r",encoding="utf-8",errors="ignore").read().lower()
        for blk in txt.split("\n\n"):
            if "handlers=" in blk and "mouse" in blk and "touchpad" not in blk:
                # Try to exclude internal by looking for i2c/serio/platform hints
                if "phys=" in blk and ("i2c" in blk or "serio" in blk):
                    continue
                return True
    except Exception:
        pass
    return False

class ExternalMouseWatcher:
    def __init__(self, on_change):
        self.on_change = on_change
        self._ctx = None
        self._mon = None
        self._obs = None
        self._last = None
        self._running = True
        self._debounce_ts = 0

        self.available = UDEV_AVAILABLE
        if self.available:
            try:
                self._ctx = pyudev.Context()
                self._mon = pyudev.Monitor.from_netlink(self._ctx)
                self._mon.filter_by(subsystem='input')
                self._mon.start()
                self._obs = pyudev.MonitorObserver(self._mon, callback=self._udev_event, name='touchpad-tray-observer')
                self._obs.start()
                print("[i] Auto mode: using udev (SUBSYSTEM=input, ID_INPUT_MOUSE, USB/BT heuristic)")
            except Exception as e:
                print(f"[i] udev watcher unavailable: {e}")
                self.available = False

        # Initial state + safety poll
        self._refresh(initial=True)
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        self._running = False
        try:
            if self._obs:
                self._obs.stop()
        except Exception:
            pass

    def _udev_event(self, device):
        now = time.time()
        if now - self._debounce_ts < 0.15:
            return
        self._debounce_ts = now
        self._refresh()

    def _refresh(self, initial=False):
        st = None
        devices = []
        if self.available and self._ctx is not None:
            devices = enumerate_external_mice(self._ctx)
            st = bool(devices)
        if st is None:
            tmp = libinput_has_external_mouse()
            st = tmp if tmp is not None else proc_has_external_mouse()
            devices = [("libinput/poll", "pointer-cap present")] if st else []
        if st != self._last or initial:
            self._last = st
            self._last_devices = devices
            GLib.idle_add(self.on_change, st)

    def _poll_loop(self):
        while self._running:
            self._refresh()
            time.sleep(3)

    def has_external_mouse(self) -> bool:
        return bool(self._last)

    def last_devices(self):
        return getattr(self, "_last_devices", [])

# ---------- Tray (policy + override) ----------
class TouchpadTray:
    def __init__(self):
        if AppInd is None or Indicator is None:
            dlg = Gtk.MessageDialog(
                flags=0, message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE, text="AppIndicator not available.",
            )
            dlg.format_secondary_text("Install 'gir1.2-ayatanaappindicator3-0.1' and re-run.")
            dlg.connect("response", lambda *a: Gtk.main_quit())
            dlg.show_all()
            return

        self.ctrl = UnifiedController()

        # Manual override: None=Auto; True=force enabled; False=force disabled
        self.manual_override = None

        # Safe startup: enable touchpad
        self.ctrl.set_enabled(True)

        self.ind = Indicator.new(APP_ID, ICON_ENABLED, AppInd.IndicatorCategory.HARDWARE)
        self.ind.set_status(AppInd.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()

        self.toggle_item = Gtk.MenuItem()
        self.toggle_item.connect("activate", self.toggle)
        menu.append(self.toggle_item)

        self.policy_item = Gtk.MenuItem(label="Policy: Auto (disable on external mouse)")
        menu.append(self.policy_item)

        dbg = Gtk.MenuItem(label="Show Status in Terminal")
        dbg.connect("activate", self.show_status)
        menu.append(dbg)

        dbg2 = Gtk.MenuItem(label="Debug: List external-mouse devices")
        dbg2.connect("activate", self.show_devices)
        menu.append(dbg2)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        menu.append(quit_item)

        menu.show_all()
        self.ind.set_menu(menu)

        # Start watcher ALWAYS to enforce policy 1–3
        self.mouse_watcher = ExternalMouseWatcher(self._on_presence_change)

        # Apply current policy now
        self._apply_policy()
        self._refresh_menu()
        self.update_icon()
        GLib.timeout_add_seconds(3, self.update_icon)

        if IS_WAYLAND and "GNOME" not in DESKTOP:
            print(f"[i] Wayland under '{DESKTOP or '?'}' → using {self.ctrl.info()}")

    # ---------- Policy / override ----------
    def _on_presence_change(self, has_mouse: bool):
        if self.manual_override is not None:
            return False
        self._apply_policy(has_mouse=has_mouse)
        self.update_icon()
        return False

    def _apply_policy(self, has_mouse=None):
        if has_mouse is None and self.mouse_watcher:
            has_mouse = self.mouse_watcher.has_external_mouse()
        want_enabled = not bool(has_mouse)
        cur = self.ctrl.get_status()
        if want_enabled and cur != "enabled":
            self.ctrl.set_enabled(True)
        elif (not want_enabled) and cur != "disabled":
            self.ctrl.set_enabled(False)

    # ---------- UI ----------
    def _refresh_menu(self):
        st = self.ctrl.get_status()
        if self.manual_override is None:
            lbl = f"Toggle Touchpad (current: {st})"
        else:
            forced = "enabled" if self.manual_override else "disabled"
            lbl = f"Toggle Touchpad (override: {forced})"
        self.toggle_item.set_label(lbl)

        pol = "Auto (disable on external mouse)" if self.manual_override is None \
              else ("Manual override: Enabled" if self.manual_override else "Manual override: Disabled")
        self.policy_item.set_label(f"Policy: {pol}")

    def toggle(self, _):
        if self.manual_override is None:
            want = (self.ctrl.get_status() != "enabled")
            self.manual_override = want
            self.ctrl.set_enabled(want)
        else:
            self.manual_override = None
            self._apply_policy()
        self._refresh_menu()
        self.update_icon()

    def quit(self, _):
        try: self.ctrl.set_enabled(True)
        except Exception: pass
        try: os.remove(LOCKFILE)
        except Exception: pass
        try:
            if self.mouse_watcher:
                self.mouse_watcher._running = False
                self.mouse_watcher.stop()
        except Exception:
            pass
        Gtk.main_quit()

    def update_icon(self):
        st = self.ctrl.get_status()
        if st == "enabled":
            self.ind.set_icon_full(ICON_ENABLED, "Touchpad Enabled")
        elif st == "disabled":
            self.ind.set_icon_full(ICON_DISABLED, "Touchpad Disabled")
        else:
            self.ind.set_icon_full(ICON_DISABLED, "Touchpad Unknown")
        self._refresh_menu()
        return True

    def show_status(self, _):
        has_mouse = self.mouse_watcher.has_external_mouse() if self.mouse_watcher else None
        print(f"[status] {self.ctrl.info()} state={self.ctrl.get_status()} external_mouse={has_mouse} override={self.manual_override}")

    def show_devices(self, _):
        devs = self.mouse_watcher.last_devices() if self.mouse_watcher else []
        print("[devices considered external]:")
        for dn, nm in devs:
            print(" -", dn, nm or "")
        if not devs:
            print(" (none)")

if __name__ == "__main__":
    TouchpadTray()
    Gtk.main()
