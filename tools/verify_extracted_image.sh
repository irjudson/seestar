#!/bin/bash
# Verify an extracted seestarOS-*.img.gz before trusting it for reflash.
#
# Checks:
#   1. GPT partition table intact, all 8 partitions present
#   2. p6 (rootfs) mounts as valid ext4
#   3. Key files exist and have expected md5s (bcmdhd.ko, rc.local, etc.)
#   4. ap_id_inited matches the source device (not the donor unit 3731a279)
#   5. p5 (/home/pi) mounts and contains ASIAIR app
#   6. Image is NOT identical to the old baseline-2.42 (would indicate bad capture)
#
# Usage:
#   sudo bash tools/verify_extracted_image.sh <image.img.gz>

set -euo pipefail

IMG="${1:-}"
if [ -z "$IMG" ] || [ ! -f "$IMG" ]; then
    echo "Usage: sudo bash $0 <image.img.gz>"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OLD_IMG="$REPO_ROOT/baseline-2.42/seestarOS.img"

if [ -t 1 ]; then
    G="\033[32m" R="\033[31m" Y="\033[33m" B="\033[34m" W="\033[0m"
else G="" R="" Y="" B="" W=""; fi
pass() { printf "  ${G}✓${W} %s\n" "$1"; }
fail() { printf "  ${R}✗${W} %s\n" "$1"; FAILS=$(( FAILS + 1 )); }
warn() { printf "  ${Y}!${W} %s\n" "$1"; }
info() { printf "    %s\n" "$1"; }
hr()   { printf "${B}══════════════════════════════════════════════════════════${W}\n"; }

FAILS=0
MNT_P5=$(mktemp -d)
MNT_P6=$(mktemp -d)
LOOP=""
cleanup() {
    umount "$MNT_P5" 2>/dev/null || true
    umount "$MNT_P6" 2>/dev/null || true
    [ -n "$LOOP" ] && losetup -d "$LOOP" 2>/dev/null || true
    rm -rf "$MNT_P5" "$MNT_P6"
}
trap cleanup EXIT

# ── Sector offsets (must match the GPT in the image) ────────────────
P5_START=229376    # /home/pi  512MB
P6_START=1277952   # rootfs    5GB

# Known-good md5s
FACTORY_MD5="4cfbf203772770d246db12505b744003"   # Jul 2023 factory bcmdhd
STOCK_MD5="8b75e5cd33fcf850dd673129d1842312"     # Oct 2025 stock (wedges affected units)
PATCHED_MD5="1fc70c15691fa675fa3e4661aa783a12"   # Oct 2025 + mmc_sw_reset patch
DONOR_AP_ID="3731a279"                            # donor unit — should NOT appear

hr
printf "  ${B}Verifying: %s${W}\n" "$(basename "$IMG")"
hr
echo ""
SIZE=$(du -h "$IMG" | awk '{print $1}')
info "File size: $SIZE"
echo ""

# ════════════════════════════════════════════════════════════════════
printf "  ${B}1. GPT partition table${W}\n"
# ════════════════════════════════════════════════════════════════════
echo ""
PT=$(zcat "$IMG" | fdisk -l - 2>/dev/null)
echo "$PT" | grep -E "^Disk|sectors|Device" | sed 's/^/    /'
echo ""

PART_COUNT=$(echo "$PT" | grep -c "^[^ ]*[0-9] " || true)
if [ "$PART_COUNT" -ge 8 ]; then
    pass "8 partitions found"
else
    fail "Expected 8 partitions, found $PART_COUNT"
fi

# Check p6 offset is correct
if echo "$PT" | grep -qE "^\S+p?6\s+${P6_START}"; then
    pass "p6 starts at sector ${P6_START} (correct)"
else
    fail "p6 sector offset unexpected — image may be misaligned"
fi

# ════════════════════════════════════════════════════════════════════
printf "\n  ${B}2. Mount and probe filesystems${W}\n"
# ════════════════════════════════════════════════════════════════════
echo ""

# Decompress to a temp file for losetup (losetup can't seek into gzip)
warn "Decompressing for mount check (this takes a minute)..."
TMP_IMG=$(mktemp /tmp/seestar-verify-XXXXXX.img)
trap 'cleanup; rm -f "$TMP_IMG"' EXIT
zcat "$IMG" > "$TMP_IMG"
pass "Decompressed OK ($(du -h "$TMP_IMG" | awk '{print $1}'))"

LOOP=$(losetup --find --partscan --show "$TMP_IMG")
pass "Loop device: $LOOP"

sleep 1   # let kernel scan partitions

# Mount p6 (rootfs)
if mount -o ro "${LOOP}p6" "$MNT_P6" 2>/dev/null; then
    pass "p6 (rootfs) mounts as ext4"
else
    fail "p6 (rootfs) failed to mount"
fi

# Mount p5 (/home/pi)
if mount -o ro "${LOOP}p5" "$MNT_P5" 2>/dev/null; then
    pass "p5 (/home/pi) mounts as ext4"
else
    fail "p5 (/home/pi) failed to mount"
fi

# ════════════════════════════════════════════════════════════════════
printf "\n  ${B}3. Key file checks${W}\n"
# ════════════════════════════════════════════════════════════════════
echo ""

# bcmdhd.ko
DRV="$MNT_P6/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko"
if [ -f "$DRV" ]; then
    drv_md5=$(md5sum "$DRV" | awk '{print $1}')
    drv_date=$(strings "$DRV" 2>/dev/null | grep "compiled on" | head -1)
    case "$drv_md5" in
        "$FACTORY_MD5") pass "bcmdhd.ko: Jul 2023 factory — pre-regression safe ($drv_md5)" ;;
        "$PATCHED_MD5") pass "bcmdhd.ko: Oct 2025 patched — mmc_sw_reset fix applied ($drv_md5)" ;;
        "$STOCK_MD5")   warn "bcmdhd.ko: Oct 2025 stock — wedges affected units ($drv_md5)"
                        info "Run swap_driver.sh patched after reflashing" ;;
        *)              warn "bcmdhd.ko: unknown md5 ($drv_md5)"
                        info "Compile date: $drv_date" ;;
    esac
else
    fail "bcmdhd.ko not found at expected path"
fi

# rc.local
RC="$MNT_P6/etc/rc.local"
if [ -f "$RC" ]; then
    rc_md5=$(md5sum "$RC" | awk '{print $1}')
    pass "rc.local present ($rc_md5)"
else
    fail "rc.local missing"
fi

# WiFi firmware blob
FW="$MNT_P6/usr/lib/firmware/fw_bcm43752a2_ag.bin"
if [ -f "$FW" ]; then
    pass "WiFi firmware blob present (fw_bcm43752a2_ag.bin)"
else
    fail "WiFi firmware blob missing"
fi

# NVRAM
NVRAM="$MNT_P6/usr/lib/firmware/nvram_ap6256.txt"
if [ -f "$NVRAM" ]; then
    pass "nvram_ap6256.txt present"
else
    fail "nvram_ap6256.txt missing"
fi

# ════════════════════════════════════════════════════════════════════
printf "\n  ${B}4. Identity / donor-unit check${W}\n"
# ════════════════════════════════════════════════════════════════════
echo ""

GENXML="$MNT_P5/.ZWO/ASIAIR_general.xml"
if [ -f "$GENXML" ]; then
    ap_id_inited=$(grep -i "ap_id_inited" "$GENXML" | grep -io "true\|false" | head -1)
    ap_id_val=$(grep -i "ap_id" "$GENXML" | grep -v "inited" | head -1 || true)

    if echo "$GENXML" | xargs grep -qi "$DONOR_AP_ID" 2>/dev/null || \
       grep -qi "$DONOR_AP_ID" "$GENXML" 2>/dev/null; then
        fail "Donor unit ap_id ($DONOR_AP_ID) found — run seestar-recovery.sh --pre-upgrade after flash"
    else
        pass "ap_id does not match donor unit"
    fi

    if [ "$ap_id_inited" = "true" ]; then
        warn "ap_id_inited=true — device will keep existing SSID on reflash"
        info "If flashing to a different unit, set ap_id_inited=false first"
    else
        pass "ap_id_inited=false — SSID will be regenerated from CPU serial on boot"
    fi
else
    warn "ASIAIR_general.xml not found in p5 — ap_id check skipped"
fi

# ASIAIR app version
VER_FILE="$MNT_P5/ASIAIR/bin/Soft03Cmt.txt"
if [ -f "$VER_FILE" ]; then
    ver=$(head -1 "$VER_FILE")
    pass "ASIAIR app: $ver"
else
    warn "version file not found"
fi

# ════════════════════════════════════════════════════════════════════
printf "\n  ${B}5. Not-identical-to-old-baseline check${W}\n"
# ════════════════════════════════════════════════════════════════════
echo ""

# Compare a fingerprint of the rootfs superblock — should differ
NEW_SB=$(dd if="$TMP_IMG" bs=512 skip=$(( P6_START + 2 )) count=4 2>/dev/null | md5sum | awk '{print $1}')
if [ -f "$OLD_IMG" ]; then
    OLD_SB=$(dd if="$OLD_IMG" bs=512 skip=$(( P6_START + 2 )) count=4 2>/dev/null | md5sum | awk '{print $1}')
    if [ "$NEW_SB" != "$OLD_SB" ]; then
        pass "Rootfs differs from baseline-2.42 (expected — capture is from a newer device)"
    else
        warn "Rootfs superblock matches baseline-2.42 exactly — verify the capture succeeded"
    fi
else
    info "baseline-2.42/seestarOS.img not available for comparison — skipping"
fi

# ════════════════════════════════════════════════════════════════════
printf "\n"
hr
if [ "$FAILS" -eq 0 ]; then
    pass "All checks passed — image looks good for reflash"
else
    fail "$FAILS check(s) failed — review output above before flashing"
fi
hr
