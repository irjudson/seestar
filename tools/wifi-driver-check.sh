#!/bin/bash
# Driver-centric diagnostic for the bcmdhd.ko Wi-Fi wedge (supersedes
# the older DT-property check).
#
# Background: we previously screened units with
#     ls /proc/device-tree/dwmmc@ffc70000/ | grep hw-reset
# assuming a missing `cap-mmc-hw-reset` property identified the affected
# cohort. Field data from multiple owners (both working and broken
# units) now shows that property is absent on every S50 DTB sampled.
# So the DT check is non-discriminating and cannot be used as a
# screening test. Instead, fingerprint the driver currently on disk
# and look for wedge evidence in dmesg.
#
# Verdicts (single uppercase token on last line of output):
#     FACTORY_SAFE      — Jul 2023 factory driver, pre-regression
#     PATCHED_SAFE      — Oct 2025 driver with mmc_hw_reset → mmc_sw_reset
#                         objcopy fix already applied
#     WEDGED_NOW        — stock Oct 2025 driver AND HT Avail timeouts in
#                         current dmesg (chip is wedged right now)
#     REGRESSED_AT_RISK — stock Oct 2025 driver but no HT Avail timeouts
#                         yet this boot. Unit may or may not wedge; some
#                         production units run this driver indefinitely
#                         without issue. If you want certainty, install
#                         the patched or factory driver.
#     UNKNOWN_DRIVER    — md5 is not in our fingerprint table (custom
#                         rebuild, future ZWO release, or mismatched
#                         firmware family)
#
# Usage:
#     ./tools/wifi-driver-check.sh [--ip 169.254.100.100]
#     On-device:  sudo bash wifi-driver-check.sh --local

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE=ssh
if [ "${1:-}" = "--local" ]; then MODE=local; shift || true; fi
. "$REPO_ROOT/tools/lib/common.sh" "$@"

# ── Probe the device ───────────────────────────────────────────────
# All grouped into one remote exec to keep latency low and output atomic.
probe_cmd='
set -u
DRV=/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko
if [ ! -f "$DRV" ]; then
    echo "DRIVER_MISSING"
    exit 0
fi
md5sum "$DRV" | awk "{print \$1}"
echo "---"
strings "$DRV" 2>/dev/null | grep -E "^compiled on " | head -1
echo "---"
sudo dmesg 2>/dev/null | grep -cE "HT Avail timeout \(1000000\): clkctl 0x50"
echo "---"
sudo dmesg 2>/dev/null | grep -iE "bcmdhd|dhd_bus|ANDROID-ERROR" | tail -8
echo "---"
cat /sys/firmware/devicetree/base/model 2>/dev/null | tr -d "\0"
'

if [ "$MODE" = "ssh" ]; then
    echo "Target: pi@${IP}"
    RAW=$($SSH "$probe_cmd" 2>&1) || { fail "SSH probe failed"; exit 1; }
else
    RAW=$(bash -c "$probe_cmd")
fi
echo ""

# If the driver file itself was missing, bail early.
if echo "$RAW" | head -1 | grep -q '^DRIVER_MISSING$'; then
    fail "bcmdhd.ko not found at expected path on device"
    echo "UNKNOWN_DRIVER"
    exit 2
fi

driver_md5=$(echo "$RAW"   | awk 'BEGIN{s=0} /^---$/{s++;next} s==0{print}' | head -1)
compile_str=$(echo "$RAW"  | awk 'BEGIN{s=0} /^---$/{s++;next} s==1{print}')
ht_count=$(echo "$RAW"     | awk 'BEGIN{s=0} /^---$/{s++;next} s==2{print}' | head -1)
dmesg_tail=$(echo "$RAW"   | awk 'BEGIN{s=0} /^---$/{s++;next} s==3{print}')
model=$(echo "$RAW"        | awk 'BEGIN{s=0} /^---$/{s++;next} s==4{print}')

# ── Classify ───────────────────────────────────────────────────────
class=$(classify_driver "$driver_md5")

echo "  Model:             ${model:-<unknown>}"
echo "  Driver md5:        $driver_md5"
echo "  Driver compile:    ${compile_str:-<unknown>}"
echo "  Classification:    $class"
echo "  HT Avail timeouts: ${ht_count:-0} (this boot)"
echo ""

case "$class" in
    factory)
        pass "Jul 2023 factory driver — pre-regression, safe."
        info "Note: every future firmware push will overwrite this."
        info "      Use ./tools/prepare_for_upgrade.sh before upgrading."
        VERDICT=FACTORY_SAFE
        ;;
    patched)
        pass "Oct 2025 driver with mmc_hw_reset→mmc_sw_reset objcopy fix — safe."
        info "Note: every future firmware push will overwrite this."
        VERDICT=PATCHED_SAFE
        ;;
    stock-wedges)
        if [ "${ht_count:-0}" -gt 0 ]; then
            fail "Stock Oct 2025 driver AND ${ht_count} HT Avail timeouts in dmesg."
            info "Chip is wedged. Symptom: sound-33 loop, AP down, LED may blink red."
            info "Fix:  ./tools/swap_driver.sh patched --ip $IP"
            VERDICT=WEDGED_NOW
        else
            warn "Stock Oct 2025 driver on disk, no wedge observed this boot."
            info "This driver regresses on *some* S50 units and works fine on others."
            info "If Wi-Fi is working for you, you may keep using it — but a suspend"
            info "or idle cycle can trigger the wedge later. For certainty, install"
            info "the patched driver:  ./tools/swap_driver.sh patched --ip $IP"
            VERDICT=REGRESSED_AT_RISK
        fi
        ;;
    unknown|*)
        warn "Unrecognised driver md5. Not in our fingerprint table."
        info "Known-good fingerprints:"
        info "  $FACTORY_MD5  Jul 2023 factory"
        info "  $PATCHED_OCT25_MD5  Oct 2025 + mmc_sw_reset patch"
        info "  $STOCK_OCT25_MD5  Oct 2025 stock (regresses on some units)"
        VERDICT=UNKNOWN_DRIVER
        ;;
esac

# ── Recent driver-related dmesg (informational only) ───────────────
if [ -n "$dmesg_tail" ]; then
    echo ""
    echo "Recent driver/bus messages (last 8 lines):"
    echo "$dmesg_tail" | sed 's/^/    /'
fi

echo ""
hr
echo "$VERDICT"
