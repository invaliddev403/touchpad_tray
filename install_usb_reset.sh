#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[*] install_usb_reset.sh is kept as a compatibility wrapper."
exec "$SCRIPT_DIR/install_touchpad_tray.sh" --with-usb-reset
