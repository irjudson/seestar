#!/bin/bash
# One-shot: is this Seestar affected by the Oct 2025 bcmdhd.ko / mmc_hw_reset bug?
#
# Affected devices have a DTB dwmmc@ffc70000 node (the SDIO bus for the
# Wi-Fi chip) that lacks the `cap-mmc-hw-reset` property. When the Oct
# 2025 Rockchip rebuild of bcmdhd.ko calls mmc_hw_reset() during chip
# init, the mmc subsystem returns -EOPNOTSUPP, leaving the SDIO bus in
# a state where the chip never grants HT clock. Result: `HT Avail
# timeout (1000000): clkctl 0x50` in dmesg → chip wedged → sound-33
# loop (en33.wav).
#
# Usage:
#   ./tools/check_if_affected.sh [--ip 169.254.100.100]
#   (on-device: sudo bash check_if_affected.sh --local)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE=ssh
if [ "${1:-}" = "--local" ]; then MODE=local; shift || true; fi
. "$REPO_ROOT/tools/lib/common.sh" "$@"

probe_cmd='
ls /proc/device-tree/dwmmc@ffc70000/ 2>/dev/null
echo "---"
sudo grep " T mmc_hw_reset" /proc/kallsyms 2>/dev/null
echo "---"
sudo dmesg | grep -cE "HT Avail timeout \(1000000\): clkctl 0x50"
echo "---"
cat /sys/firmware/devicetree/base/model
'

if [ "$MODE" = "ssh" ]; then
    echo "Target: pi@${IP}"
    PROPS=$($SSH "$probe_cmd" 2>&1)
else
    PROPS=$(bash -c "$probe_cmd")
fi
echo ""

dt_props=$(echo "$PROPS" | awk 'BEGIN{s=0} /^---$/{s++;next} s==0{print}')
kernel_exports_hw_reset=$(echo "$PROPS" | awk 'BEGIN{s=0} /^---$/{s++;next} s==1{print}')
ht_avail_count=$(echo "$PROPS" | awk 'BEGIN{s=0} /^---$/{s++;next} s==2{print}')
model=$(echo "$PROPS" | awk 'BEGIN{s=0} /^---$/{s++;next} s==3{print}' | tr -d '\0')

echo "DTB dwmmc@ffc70000 properties:"
echo "$dt_props" | sed 's/^/    /'
echo ""
echo "Model: $model"
echo ""

if echo "$dt_props" | grep -q '^cap-mmc-hw-reset$'; then
    pass "DTB HAS cap-mmc-hw-reset → NOT affected"
    VERDICT=clean
else
    fail "DTB MISSING cap-mmc-hw-reset → AFFECTED"
    VERDICT=affected
fi

if [ -n "$kernel_exports_hw_reset" ]; then
    info "kernel exports mmc_hw_reset (expected on 4.19.111)"
else
    warn "kernel does not export mmc_hw_reset (unusual)"
fi

echo ""
echo "HT Avail timeout count in current dmesg: $ht_avail_count"
if [ "${ht_avail_count:-0}" -gt 0 ]; then
    info "→ chip has wedged this boot (confirms affected AND running stock Oct 2025 driver)"
elif [ "$VERDICT" = "affected" ]; then
    info "→ 0, so either (a) running factory Jul 2023 / patched Oct 2025 driver, or (b) self-healed"
fi

echo ""
echo "Summary: device is $VERDICT"
if [ "$VERDICT" = "affected" ]; then
    echo ""
    echo "To deploy the working patched Oct 2025 driver:"
    echo "    ./tools/swap_driver.sh patched --ip $IP"
    echo ""
    echo "Or the factory Jul 2023 driver:"
    echo "    ./tools/swap_driver.sh factory --ip $IP"
fi
