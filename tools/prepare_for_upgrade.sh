#!/bin/bash
# Pre-upgrade prep for any iscope firmware push on an AFFECTED Seestar.
# Stages a known-good driver + post-upgrade swap script on the device in
# persistent storage at /home/pi/, so recovery from the wedge is a one-line
# SSH command after the upgrade lands.
#
# Usage:
#   ./tools/prepare_for_upgrade.sh [--to factory|patched] [--ip 169.254.100.100]
#
#   --to factory   stage Jul 2023 factory driver (default)
#   --to patched   stage Oct 2025 mmc_sw_reset-patched driver
#
# Recovery procedure after the iscope upgrade completes:
#   1. Let your push tool land the new firmware (chip will wedge).
#   2. ssh pi@<ip>   (USB-ethernet still works)
#   3. sudo /home/pi/post_upgrade_swap.sh
#   4. wait ~90s for reboot
#   5. ./tools/verify_functional.sh --ip <ip>

set -e
MODE=factory
# Parse --to before passing remaining args to common.sh for --ip
while [ $# -gt 0 ]; do
    case "$1" in
        --to) MODE="$2"; shift 2 ;;
        *) break ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$REPO_ROOT/tools/lib/common.sh" "$@"

case "$MODE" in
    factory) LOCAL_KO="$FACTORY_KO"; WANT_MD5="$FACTORY_MD5"; LABEL="factory Jul 2023" ;;
    patched) LOCAL_KO="$PATCHED_KO"; WANT_MD5="$PATCHED_OCT25_MD5"; LABEL="patched Oct 2025" ;;
    *) echo "Usage: $0 [--to factory|patched] [--ip <addr>]"; exit 1 ;;
esac

STAMP=$(date +%Y%m%d-%H%M%S)
SNAPSHOT_DIR="$REPO_ROOT/analysis/pre_upgrade_snapshot_${STAMP}"

hr
echo "  Pre-upgrade prep (staging $LABEL driver)"
echo "  Target:       pi@$IP"
echo "  Snapshot dir: $SNAPSHOT_DIR"
hr

# ── 0. Sanity checks ───────────────────────────────────────────────────
if [ ! -f "$LOCAL_KO" ]; then
    fail "local driver not found at $LOCAL_KO"
    [ "$MODE" = "factory" ] && info "Run: ./tools/extract_factory_bcmdhd.sh"
    exit 1
fi
local_md5=$(md5sum "$LOCAL_KO" | awk '{print $1}')
if [ "$local_md5" != "$WANT_MD5" ]; then
    fail "local driver md5 mismatch: $local_md5 (expected $WANT_MD5)"
    exit 1
fi
pass "local driver verified (md5 $WANT_MD5)"
require_ssh
pass "SSH OK"

mkdir -p "$SNAPSHOT_DIR"

# ── 1. Snapshot current state ──────────────────────────────────────────
echo ""
echo "[1/5] Capturing pre-upgrade snapshot..."
$SSH 'grep -E "^version_" /home/pi/ASIAIR/config 2>/dev/null' > "$SNAPSHOT_DIR/fw_version.txt" || true
$SSH "md5sum $DRIVER_PATH" > "$SNAPSHOT_DIR/current_driver_md5.txt"
$SSH "strings $DRIVER_PATH | grep 'compiled on' | head -1" > "$SNAPSHOT_DIR/current_driver_date.txt"
$SSH "cat $SH_CONF 2>/dev/null" > "$SNAPSHOT_DIR/sh_conf.txt" || true
$SSH 'sudo wl country 2>&1' > "$SNAPSHOT_DIR/wl_country.txt" || true
$SSH 'ip link show wlan0 2>&1; ip link show uap0 2>&1' > "$SNAPSHOT_DIR/ip_links.txt" || true
$SSH 'cat /home/pi/en_eth 2>/dev/null' > "$SNAPSHOT_DIR/en_eth.txt" || true
$SSH 'sudo dmesg -T | tail -100' > "$SNAPSHOT_DIR/dmesg_tail.txt" || true
info "saved to $SNAPSHOT_DIR/"

current_md5=$(awk '{print $1}' "$SNAPSHOT_DIR/current_driver_md5.txt")
current_class=$(classify_driver "$current_md5")
info "current driver: $current_md5  ($current_class)"

# ── 2. Stage driver on device ──────────────────────────────────────────
echo ""
echo "[2/5] Staging $LABEL driver at /home/pi/bcmdhd.ko.staged..."
$SCP "$LOCAL_KO" pi@${IP}:/home/pi/bcmdhd.ko.staged
$SSH "md5sum /home/pi/bcmdhd.ko.staged | grep -q $WANT_MD5 && echo '    [✓] staged, md5 verified'"

# ── 3. Write post-upgrade swap script on device ────────────────────────
echo ""
echo "[3/5] Writing /home/pi/post_upgrade_swap.sh on device..."
$SSH "cat > /home/pi/post_upgrade_swap.sh <<'POSTUPGRADE'
#!/bin/bash
# Post-upgrade: replace whatever driver the upgrade pushed with our
# pre-staged known-good one, then reboot.
set -e
STAGED=/home/pi/bcmdhd.ko.staged
WANT_MD5=$WANT_MD5
TARGET=$DRIVER_PATH

if [ ! -f \"\$STAGED\" ]; then echo 'ERROR: staged driver missing'; exit 1; fi
if ! md5sum \"\$STAGED\" | grep -q \"\$WANT_MD5\"; then echo 'ERROR: staged driver md5 mismatch'; exit 1; fi

echo '[post-upgrade] current driver:'
md5sum \"\$TARGET\"
strings \"\$TARGET\" | grep 'compiled on' | head -1

echo '[post-upgrade] remounting / rw...'
sudo mount -o remount,rw /
if [ ! -f \"\${TARGET}.postupgrade_backup\" ]; then
    sudo cp \"\$TARGET\" \"\${TARGET}.postupgrade_backup\"
fi
sudo cp \"\$STAGED\" \"\$TARGET\"
sudo depmod -a 2>&1 || true
sudo mount -o remount,ro / 2>/dev/null || true

echo '[post-upgrade] verifying swap...'
md5sum \"\$TARGET\"
strings \"\$TARGET\" | grep 'compiled on' | head -1

echo '[post-upgrade] rebooting in 3s...'
sleep 3
sudo reboot -f
POSTUPGRADE
chmod +x /home/pi/post_upgrade_swap.sh
ls -l /home/pi/post_upgrade_swap.sh"
info "[✓] swap script staged on device"

# ── 4. USB-ethernet recovery path check ────────────────────────────────
echo ""
echo "[4/5] USB-ethernet recovery path..."
en_eth=$(cat "$SNAPSHOT_DIR/en_eth.txt" | tr -d '\n')
info "/home/pi/en_eth = ${en_eth:-<missing>}"
if [ "$en_eth" != "1" ]; then
    warn "en_eth != 1 — USB gadget mode may not be ethernet."
    warn "If the upgrade wedges WiFi AND USB isn't ethernet, you'll need rkdeveloptool."
    warn "Fix first:  ssh pi@$IP 'echo 1 | sudo tee /home/pi/en_eth && sudo reboot'"
fi

# ── 5. Summary ─────────────────────────────────────────────────────────
echo ""
echo "[5/5] Summary"
echo ""
info "Snapshot:         $SNAPSHOT_DIR/"
info "On device:        /home/pi/bcmdhd.ko.staged  (md5 $WANT_MD5)"
info "On device:        /home/pi/post_upgrade_swap.sh"
info "Pre-upgrade fw:   $(cat "$SNAPSHOT_DIR/fw_version.txt" 2>/dev/null | tr '\n' ' ')"
info "Pre-upgrade drv:  $current_md5  ($current_class)"
echo ""
hr
echo "READY. Recovery after the upgrade wedges:"
echo ""
echo "    ssh pi@${IP} 'sudo /home/pi/post_upgrade_swap.sh'"
echo "    # wait ~90s, then:"
echo "    ./tools/verify_functional.sh --ip $IP"
echo ""
echo "If USB-ethernet dies too, fall back to rkdeveloptool reflash:"
echo "    ./tools/seestar-recovery.sh"
hr
