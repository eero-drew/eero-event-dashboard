#!/bin/bash
# =============================================================================
# MiniRack Dashboard - SD Card Prep Script (run on your Mac)
#
# After flashing Raspberry Pi OS with Raspberry Pi Imager, run this script
# to inject the MiniRack auto-installer onto the SD card's boot partition.
#
# Usage:
#   ./deploy/pi_sdcard_setup.sh
#
# Prerequisites:
#   1. Flash Raspberry Pi OS (64-bit) using Raspberry Pi Imager
#      - Set hostname, WiFi, SSH, and username/password in Imager settings
#   2. Keep the SD card mounted (boot partition appears as "bootfs")
#   3. Run this script
#   4. Eject SD card, insert into Pi 5, power on
#   5. Wait ~5-10 min, then visit http://<hostname>.local or http://<pi-ip>
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOOT_MOUNT="/Volumes/bootfs"

echo ""
echo "🍓 MiniRack Dashboard — SD Card Setup"
echo "======================================="
echo ""

# --- Check boot partition is mounted ---
if [ ! -d "$BOOT_MOUNT" ]; then
    echo -e "${RED}❌ Boot partition not found at $BOOT_MOUNT${NC}"
    echo ""
    echo "Make sure you've:"
    echo "  1. Flashed Raspberry Pi OS with Raspberry Pi Imager"
    echo "  2. The SD card is still inserted and mounted"
    echo ""
    echo "The boot partition should appear as 'bootfs' in Finder."
    echo ""

    # Check for other possible mount points
    OTHER=$(ls -d /Volumes/boot* 2>/dev/null || true)
    if [ -n "$OTHER" ]; then
        echo "Found these possible boot volumes:"
        echo "$OTHER"
        echo ""
        echo "If one of these is correct, run:"
        echo "  BOOT_MOUNT=/Volumes/<name> $0"
    fi
    exit 1
fi

echo -e "${GREEN}✅ Found boot partition at $BOOT_MOUNT${NC}"

# --- Copy firstrun script ---
# Raspberry Pi OS uses /boot/firmware/firstrun.sh (or cmdline.txt modification)
# We'll use the rc.local approach which is more reliable across OS versions.

echo "📋 Installing first-boot auto-installer..."

# Create a script that will be called via rc.local on first boot
cat > /tmp/minirack_firstboot.sh << 'FBEOF'
#!/bin/bash
# MiniRack auto-installer — runs once on first boot, then removes itself

MARKER="/opt/eero/.installed"
LOG="/var/log/minirack-firstboot.log"

# Only run once
if [ -f "$MARKER" ]; then
    exit 0
fi

exec > >(tee -a "$LOG") 2>&1
echo "$(date) - MiniRack first-boot starting..."

# Wait for network (up to 60s)
for i in $(seq 1 30); do
    if ping -c1 -W2 8.8.8.8 &>/dev/null; then
        echo "Network is up"
        break
    fi
    echo "Waiting for network... ($i/30)"
    sleep 2
done

# Download and run installer
INSTALLER_URL="https://raw.githubusercontent.com/Drew-CodeRGV/eero-event-dashboard/main/deploy/pi_installer.sh"
curl -sfL "$INSTALLER_URL" -o /tmp/pi_installer.sh
chmod +x /tmp/pi_installer.sh
bash /tmp/pi_installer.sh
rm -f /tmp/pi_installer.sh

# Mark as installed so this doesn't run again
mkdir -p /opt/eero
touch "$MARKER"

# Remove ourselves from rc.local
sed -i '/minirack_firstboot/d' /etc/rc.local 2>/dev/null || true
rm -f /opt/minirack_firstboot.sh

echo "$(date) - MiniRack first-boot complete!"
FBEOF

# Copy the firstboot script to the boot partition
# It will be available at /boot/firmware/ once the Pi boots
cp /tmp/minirack_firstboot.sh "$BOOT_MOUNT/minirack_firstboot.sh"
chmod +x "$BOOT_MOUNT/minirack_firstboot.sh"
rm /tmp/minirack_firstboot.sh

# Create a custom cmdline addition that triggers on first boot
# We inject into the firstrun.sh that Pi Imager creates, or create rc.local hook

# Method: Create a custom-firstrun script that Pi OS will pick up
# Pi Imager already creates firstrun.sh — we append to it if it exists,
# otherwise we set up rc.local

if [ -f "$BOOT_MOUNT/firstrun.sh" ]; then
    echo "📝 Found Pi Imager firstrun.sh — appending MiniRack installer..."

    # Insert our installer call before the final reboot/exit in firstrun.sh
    # Pi Imager's firstrun.sh typically ends with "rm -f /boot/firstrun.sh" and reboot
    # We add our script to run after the Pi Imager setup but before cleanup

    cat >> "$BOOT_MOUNT/firstrun.sh" << 'APPENDEOF'

# --- MiniRack Dashboard Auto-Install ---
cp /boot/firmware/minirack_firstboot.sh /opt/minirack_firstboot.sh 2>/dev/null || \
cp /boot/minirack_firstboot.sh /opt/minirack_firstboot.sh 2>/dev/null || true
chmod +x /opt/minirack_firstboot.sh 2>/dev/null || true

# Add to rc.local to run after reboot (network will be available then)
if [ -f /etc/rc.local ]; then
    sed -i '/^exit 0/i /opt/minirack_firstboot.sh &' /etc/rc.local
else
    cat > /etc/rc.local << 'RCEOF'
#!/bin/bash
/opt/minirack_firstboot.sh &
exit 0
RCEOF
    chmod +x /etc/rc.local
fi
# --- End MiniRack ---
APPENDEOF

    echo -e "${GREEN}✅ Appended to existing firstrun.sh${NC}"
else
    echo "📝 No Pi Imager firstrun.sh found — creating rc.local hook..."

    # Create a firstrun.sh that sets up rc.local
    cat > "$BOOT_MOUNT/firstrun.sh" << 'NEWRUNEOF'
#!/bin/bash
set -e

# Copy installer to persistent location
cp /boot/firmware/minirack_firstboot.sh /opt/minirack_firstboot.sh 2>/dev/null || \
cp /boot/minirack_firstboot.sh /opt/minirack_firstboot.sh 2>/dev/null || true
chmod +x /opt/minirack_firstboot.sh 2>/dev/null || true

# Set up rc.local to run on next boot (after network is available)
cat > /etc/rc.local << 'RCEOF'
#!/bin/bash
/opt/minirack_firstboot.sh &
exit 0
RCEOF
chmod +x /etc/rc.local

# Clean up
rm -f /boot/firmware/firstrun.sh /boot/firstrun.sh

# Reboot to trigger rc.local with network
reboot
NEWRUNEOF
    chmod +x "$BOOT_MOUNT/firstrun.sh"
    echo -e "${GREEN}✅ Created firstrun.sh${NC}"
fi

echo ""
echo "============================================="
echo -e "${GREEN}✅ SD card is ready!${NC}"
echo "============================================="
echo ""
echo "  Next steps:"
echo "  1. Eject the SD card from your Mac"
echo "  2. Insert it into your Raspberry Pi 5"
echo "  3. Power on the Pi"
echo "  4. Wait 5-10 minutes for setup to complete"
echo "  5. Open http://<pi-hostname>.local in your browser"
echo ""
echo "  The Pi will:"
echo "    → Boot Raspberry Pi OS"
echo "    → Connect to WiFi (configured in Imager)"
echo "    → Auto-install MiniRack Dashboard"
echo "    → Start serving on port 80"
echo ""
echo "  To check progress, SSH in and run:"
echo "    tail -f /var/log/minirack-firstboot.log"
echo "============================================="
