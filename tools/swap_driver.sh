#!/bin/bash
# Swap the Wi-Fi driver (bcmdhd.ko) on a live Seestar to a known-good variant.
# Replaces the two older one-shot scripts (swap_bcmdhd_to_factory.sh and
# test_oct2025_with_sw_reset.sh) with a single tool that picks the target.
#
# Usage:
#   ./tools/swap_driver.sh <factory|patched> [--ip 169.254.100.100]
#
#   factory   — install Jul 2023 factory driver (md5 4cfbf203...)
#               Extracted from baseline-2.42/seestarOS.img partition 6.
#               Stock pre-regression driver; verified working.
#
#   patched   — install Oct 2025 driver with mmc_hw_reset → mmc_sw_reset
#               (md5 1fc70c15...). Produced via:
#                 arm-linux-gnueabihf-objcopy --redefine-sym \
#                   mmc_hw_reset=mmc_sw_reset <stock> <patched>
#               Same binary as stock Oct 2025 in every other way;
#               verified working.
#
# After the swap the device reboots and you should run verify_functional.sh
# to confirm. Backup of whatever was installed goes to
# ${DRIVER_PATH}.prior_to_swap on the device (non-overwriting).

set -e
MODE="${1:-}"
shift || true

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$REPO_ROOT/tools/lib/common.sh" "$@"

case "$MODE" in
    factory)
        SRC_KO="$FACTORY_KO"
        WANT_MD5="$FACTORY_MD5"
        LABEL="factory Jul 2023"
        ;;
    patched)
        SRC_KO="$PATCHED_KO"
        WANT_MD5="$PATCHED_OCT25_MD5"
        LABEL="patched Oct 2025 (mmc_hw_reset→mmc_sw_reset)"
        ;;
    *)
        echo "Usage: $0 <factory|patched> [--ip 169.254.100.100]"
        exit 1
        ;;
esac

hr
echo "  Seestar driver swap → $LABEL"
echo "  target: pi@${IP}"
hr

# ── 1. Verify local artifact exists and matches expected md5 ────────────
if [ ! -f "$SRC_KO" ]; then
    fail "Local driver not found at $SRC_KO"
    if [ "$MODE" = "factory" ]; then
        info "Run: ./tools/extract_factory_bcmdhd.sh"
    else
        info "The patched driver should be at firmware/experimental/."
        info "Rebuild with:"
        info "  arm-linux-gnueabihf-objcopy --redefine-sym mmc_hw_reset=mmc_sw_reset \\"
        info "    firmware/packages/fw_2.6.4/others/bcmdhd.ko  $SRC_KO"
    fi
    exit 1
fi
local_md5=$(md5sum "$SRC_KO" | awk '{print $1}')
if [ "$local_md5" != "$WANT_MD5" ]; then
    fail "Local driver md5 mismatch: got $local_md5 (expected $WANT_MD5)"
    exit 1
fi
pass "local driver verified: md5 $WANT_MD5"

require_ssh
pass "SSH to pi@${IP}"

# ── 2. Capture current driver info on device ───────────────────────────
echo ""
echo "[1/4] Current driver on device:"
$SSH "md5sum $DRIVER_PATH ; strings $DRIVER_PATH | grep 'compiled on' | head -1" | sed 's/^/    /'

# ── 3. Upload ──────────────────────────────────────────────────────────
echo ""
echo "[2/4] Upload to /tmp..."
$SCP "$SRC_KO" pi@${IP}:/tmp/bcmdhd.ko.new
$SSH "md5sum /tmp/bcmdhd.ko.new | grep -q $WANT_MD5 && echo '    [✓] upload md5 verified'"

# ── 4. Install on device ───────────────────────────────────────────────
echo ""
echo "[3/4] Remount rw, backup current, install, depmod..."
$SSH "
set -e
sudo mount -o remount,rw /
if [ ! -f '${DRIVER_PATH}.prior_to_swap' ]; then
    sudo cp '$DRIVER_PATH' '${DRIVER_PATH}.prior_to_swap'
    echo '    [✓] backup saved as .prior_to_swap'
else
    echo '    [=] .prior_to_swap backup already present (not overwriting)'
fi
sudo cp /tmp/bcmdhd.ko.new '$DRIVER_PATH'
sudo depmod -a 2>&1 || echo '    (depmod warning non-fatal; cp was the load-bearing step)'
sudo mount -o remount,ro / 2>/dev/null || true
md5sum '$DRIVER_PATH'
strings '$DRIVER_PATH' | grep 'compiled on' | head -1
"

# ── 5. Reboot ──────────────────────────────────────────────────────────
echo ""
echo "[4/4] Rebooting..."
$SSH 'sudo reboot -f' || true
info "(ssh exits 255 on reboot — expected)"

echo ""
hr
echo "Wait ~90s, then verify:"
echo "    ./tools/verify_functional.sh --ip $IP"
hr
