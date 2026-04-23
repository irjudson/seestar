#!/bin/bash
# Extract the factory bcmdhd.ko from baseline-2.42/seestarOS.img and compare
# it with what fw_2.6.4+ ships.
#
# Hypothesis: fw_2.6.1 (5.50) keeps the factory driver (Jul 2023 build, which
# works on this chip). fw_2.6.4+ (5.82+) installs a NEWER build (Oct 2025)
# via update_package.sh's replace_file_reboot, which regresses chip init
# (HT Avail timeout, chip never locks HT PLL).
#
# This script:
#   1. Loop-mounts the baseline-2.42 seestarOS.img
#   2. Pulls /lib/modules/.../bcmdhd.ko out of partition 6 (rootfs)
#   3. Reports its md5 + compile-date string
#   4. Compares with the driver shipped by fw_2.6.4
#   5. Saves the factory driver to firmware/factory/bcmdhd.ko.jul2023
#
# Requires sudo (losetup + mount).

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG="$REPO_ROOT/baseline-2.42/seestarOS.img"
OUT_DIR="$REPO_ROOT/firmware/factory"
MOUNT="/mnt/baseline_rootfs_$$"
NEW_KO="$REPO_ROOT/firmware/packages/fw_2.6.4/others/bcmdhd.ko"

if [ ! -f "$IMG" ]; then
    echo "ERROR: $IMG not found"; exit 1
fi
if [ ! -f "$NEW_KO" ]; then
    echo "ERROR: $NEW_KO not found"; exit 1
fi

mkdir -p "$OUT_DIR"
sudo mkdir -p "$MOUNT"

echo "[1/5] Attaching $IMG as loop device..."
LOOP=$(sudo losetup -Pf --show "$IMG")
echo "    loop=$LOOP"

cleanup() {
    sudo umount "$MOUNT" 2>/dev/null || true
    sudo losetup -d "$LOOP" 2>/dev/null || true
    sudo rmdir "$MOUNT" 2>/dev/null || true
}
trap cleanup EXIT

echo "[2/5] Mounting ${LOOP}p6 (rootfs) read-only..."
sudo mount -o ro "${LOOP}p6" "$MOUNT"

KO_PATH="$MOUNT/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko"
if [ ! -f "$KO_PATH" ]; then
    echo "ERROR: bcmdhd.ko not found in factory image at expected path"
    echo "       looked at: $KO_PATH"
    exit 1
fi

echo "[3/5] Extracting factory bcmdhd.ko..."
sudo cp "$KO_PATH" "$OUT_DIR/bcmdhd.ko.jul2023"
sudo chown "$(whoami)" "$OUT_DIR/bcmdhd.ko.jul2023"
echo "    saved to: $OUT_DIR/bcmdhd.ko.jul2023"

echo ""
echo "[4/5] Compare factory driver (from baseline-2.42) vs fw_2.6.4 driver:"
echo ""
FACT_MD5=$(md5sum "$OUT_DIR/bcmdhd.ko.jul2023" | awk '{print $1}')
NEW_MD5=$(md5sum "$NEW_KO" | awk '{print $1}')
FACT_DATE=$(strings "$OUT_DIR/bcmdhd.ko.jul2023" | grep "compiled on" | head -1)
NEW_DATE=$(strings "$NEW_KO" | grep "compiled on" | head -1)
FACT_SIZE=$(stat -c %s "$OUT_DIR/bcmdhd.ko.jul2023")
NEW_SIZE=$(stat -c %s "$NEW_KO")

printf "  %-30s %s\n" "factory (baseline-2.42):" "md5=$FACT_MD5"
printf "  %-30s %s\n" "" "size=$FACT_SIZE"
printf "  %-30s %s\n" "" "$FACT_DATE"
echo ""
printf "  %-30s %s\n" "fw_2.6.4 replacement:" "md5=$NEW_MD5"
printf "  %-30s %s\n" "" "size=$NEW_SIZE"
printf "  %-30s %s\n" "" "$NEW_DATE"
echo ""

if [ "$FACT_MD5" = "$NEW_MD5" ]; then
    echo "[5/5] VERDICT: drivers are IDENTICAL — bcmdhd.ko is NOT the regression"
    echo "              (earlier hypothesis refuted)"
else
    echo "[5/5] VERDICT: drivers are DIFFERENT — bcmdhd.ko IS the regression vector"
    echo ""
    echo "    fw_2.6.4+'s update_package.sh replaces the factory Jul 2023 driver"
    echo "    with the Oct 2025 build. The new build regresses chip init on this S50."
    echo ""
    echo "    Next step: build iscope_2.6.4_factory_bcmdhd by substituting the"
    echo "    factory driver into the fw_2.6.4 package before repacking."
fi
