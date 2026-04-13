#!/bin/bash
# =============================================================================
# MiniRack Dashboard - Raspberry Pi First-Boot Setup
#
# This script runs ONCE on first boot, installs the dashboard, then removes
# itself. Drop this onto a freshly flashed Raspberry Pi OS SD card.
#
# Setup:
#   1. Flash Raspberry Pi OS with Raspberry Pi Imager
#   2. Mount the boot partition (shows as "bootfs" on macOS)
#   3. Run: cp deploy/pi_firstboot.sh /Volumes/bootfs/firstrun.sh
#      -- or use deploy/pi_sdcard_setup.sh to do it automatically
#   4. Eject, insert into Pi, power on
#   5. Wait ~5-10 minutes, then open http://<pi-ip> in your browser
# =============================================================================

set -e

LOG="/var/log/minirack-firstboot.log"
exec > >(tee -a "$LOG") 2>&1

echo "$(date) - MiniRack first-boot starting..."

# Wait for network
echo "Waiting for network..."
for i in $(seq 1 30); do
    if ping -c1 -W2 8.8.8.8 &>/dev/null; then
        echo "Network is up"
        break
    fi
    sleep 2
done

# Download and run the installer
INSTALLER_URL="https://raw.githubusercontent.com/Drew-CodeRGV/eero-event-dashboard/main/deploy/pi_installer.sh"

echo "Downloading installer..."
curl -sfL "$INSTALLER_URL" -o /tmp/pi_installer.sh
chmod +x /tmp/pi_installer.sh

echo "Running installer..."
bash /tmp/pi_installer.sh

# Clean up
rm -f /tmp/pi_installer.sh

echo "$(date) - MiniRack first-boot complete!"
