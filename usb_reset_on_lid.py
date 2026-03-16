#!/usr/bin/env python3
import time
import evdev
import pyudev
import os
import sys

def find_mouse_usb_devices():
    ctx = pyudev.Context()
    usb_devs = set()
    for d in ctx.list_devices(subsystem='input'):
        try:
            if d.properties.get('ID_INPUT_MOUSE') == '1' and d.properties.get('ID_INPUT_TOUCHPAD') != '1':
                parent = d.parent
                while parent is not None:
                    if parent.subsystem == 'usb' and hasattr(parent, 'device_type') and parent.device_type == 'usb_device':
                        usb_devs.add(parent.sys_path)
                        break
                    parent = parent.parent
        except Exception as e:
            print(f"Error checking device: {e}", file=sys.stderr)
    return list(usb_devs)

def reset_usb_device(sys_path):
    print(f"Resetting USB device at {sys_path}")
    auth_file = os.path.join(sys_path, "authorized")
    if not os.path.exists(auth_file):
        print(f"No authorized file found at {auth_file}")
        return
    try:
        # Disable port
        with open(auth_file, "w") as f:
            f.write("0\n")
        # Wait a brief moment
        time.sleep(1.0)
        # Re-enable port
        with open(auth_file, "w") as f:
            f.write("1\n")
        print(f"Successfully reset {sys_path}")
    except Exception as e:
        print(f"Failed to reset {sys_path}: {e}", file=sys.stderr)

def find_lid_device():
    for p in evdev.list_devices():
        try:
            dev = evdev.InputDevice(p)
            if evdev.ecodes.EV_SW in dev.capabilities():
                if evdev.ecodes.SW_LID in dev.capabilities()[evdev.ecodes.EV_SW]:
                    return p
        except Exception:
            pass
    return None

def main():
    print("Starting USB Mouse Reset Lid Monitor...")
    lid_path = find_lid_device()
    if not lid_path:
        print("Lid switch not found among input devices!")
        sys.exit(1)
        
    dev = evdev.InputDevice(lid_path)
    print(f"Listening to lid open events passively on {dev.name} ({lid_path})...")
    
    while True:
        try:
            for event in dev.read_loop():
                if event.type == evdev.ecodes.EV_SW and event.code == evdev.ecodes.SW_LID:
                    if event.value == 0:  # 0 indicates Lid Open, 1 indicates Lid Close
                        print("Lid OPENS detected. Wait for devices to settle...")
                        time.sleep(1.0) # ensure kernel devices settled
                        devs = find_mouse_usb_devices()
                        if not devs:
                            print("No external USB mice detected to reset.")
                        for d in devs:
                            reset_usb_device(d)
        except OSError:
            print("Lid switch input lost. Reconnecting in 5 seconds...")
            dev.close()
            time.sleep(5)
            # Re-poll until lid switch is found again
            while True:
                new_path = find_lid_device()
                if new_path:
                    try:
                        dev = evdev.InputDevice(new_path)
                        print(f"Reconnected to {dev.name}")
                        break
                    except Exception:
                        pass
                time.sleep(5)

if __name__ == '__main__':
    # Ensure dependencies are available and no buffer in print
    os.environ['PYTHONUNBUFFERED'] = "1"
    main()
