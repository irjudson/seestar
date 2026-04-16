#!/bin/bash
#
# Build and sign custom Seestar firmware
# Uses platform-specific update scripts
# Produces signed files named "iscope" and "iscope_64" ready to flash
#

set -e

# Platform-specific update scripts
CUSTOM_SCRIPT_X86="custom_firmware/update_package_clean_sane.sh"
CUSTOM_SCRIPT_X64="custom_firmware/update_package_64.sh"
KEY_PATH="../../astronomus/backend/secrets/seestar_private_key.pem"
WORK_DIR="build_temp"

echo "[*] Building custom firmware (both x86 and x64 versions)..."
echo "[*] Using platform-specific update scripts"

# Clean any previous build
rm -rf "$WORK_DIR" 2>/dev/null || true
rm -f firmware_unsigned.tar.bz2 iscope iscope_64 2>/dev/null || true

# Check scripts exist
if [ ! -f "$CUSTOM_SCRIPT_X86" ]; then
    echo "[!] Error: $CUSTOM_SCRIPT_X86 not found"
    exit 1
fi

if [ ! -f "$CUSTOM_SCRIPT_X64" ]; then
    echo "[!] Error: $CUSTOM_SCRIPT_X64 not found"
    exit 1
fi

# Function to build a firmware package
build_firmware() {
    local FIRMWARE_BASE="$1"
    local OUTPUT_FILE="$2"
    local CUSTOM_SCRIPT="$3"
    local PLATFORM_NAME="$4"

    echo ""
    echo "========================================="
    echo "[*] Building $PLATFORM_NAME firmware..."
    echo "========================================="

    # Check firmware base exists
    if [ ! -d "$FIRMWARE_BASE" ]; then
        echo "[!] Error: $FIRMWARE_BASE directory not found"
        return 1
    fi

    # Clean work directory
    rm -rf "$WORK_DIR" 2>/dev/null || true

    # Copy base firmware to work directory
    echo "[*] Copying firmware base from $FIRMWARE_BASE..."
    cp -r "$FIRMWARE_BASE" "$WORK_DIR"

    # Replace update_package.sh with platform-specific script
    echo "[*] Using custom update script: $CUSTOM_SCRIPT ($(stat -c %s "$CUSTOM_SCRIPT") bytes)"
    cp "$CUSTOM_SCRIPT" "$WORK_DIR/update_package.sh"
    chmod +x "$WORK_DIR/update_package.sh"

    # Create tar.bz2 package
    echo "[*] Creating tar.bz2 package..."
    tar -cjf firmware_unsigned.tar.bz2 -C "$WORK_DIR" .

    # Get size for info
    SIZE=$(stat -c %s firmware_unsigned.tar.bz2)
    echo "[+] Unsigned package: $SIZE bytes"

    # Sign the firmware
    echo "[*] Signing firmware with private key..."
    python3 sign_firmware.py firmware_unsigned.tar.bz2 "$KEY_PATH" -o "$OUTPUT_FILE"

    # Cleanup
    rm -rf "$WORK_DIR"
    rm firmware_unsigned.tar.bz2

    echo "[+] $PLATFORM_NAME firmware built: $OUTPUT_FILE"
    ls -lh "$OUTPUT_FILE"
}

# Build both versions with platform-specific scripts
build_firmware "custom_firmware/iscope_base" "iscope" "$CUSTOM_SCRIPT_X86" "X86"
build_firmware "custom_firmware/iscope_64_base" "iscope_64" "$CUSTOM_SCRIPT_X64" "X64"

echo ""
echo "========================================="
echo "[+] Build complete!"
echo "========================================="
echo "Built firmware files:"
ls -lh iscope iscope_64
echo ""
echo "Ready to flash with auto-detection:"
echo "  python3 seestar_firmware_flash.py --auto --host <device_ip>"
echo ""
echo "Or manually specify:"
echo "  python3 seestar_firmware_flash.py iscope --host <device_ip>"
echo "  python3 seestar_firmware_flash.py iscope_64 --host <device_ip>"
echo "========================================="
