# Shared constants and helpers for tools/*.sh on the Seestar project.
# Source this at the top of a tool:   . "$(dirname "$0")/lib/common.sh"

# ── Canonical paths on the device ──────────────────────────────────
DRIVER_PATH=/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko
SH_CONF=/home/pi/.ZWO/sh_conf.txt

# ── Known bcmdhd.ko md5s ───────────────────────────────────────────
# All three are known-state driver fingerprints. Scripts can compare to
# any of these. FACTORY and PATCHED are verified-working; STOCK_OCT2025
# wedges this cohort's chip.
FACTORY_MD5="4cfbf203772770d246db12505b744003"          # Jul 7 2023 — baseline-2.42 factory driver
PATCHED_OCT25_MD5="1fc70c15691fa675fa3e4661aa783a12"    # Oct 17 2025 w/ mmc_hw_reset → mmc_sw_reset
STOCK_OCT25_MD5="8b75e5cd33fcf850dd673129d1842312"      # Oct 17 2025 stock — WEDGES affected units

# ── Repo paths to the driver files we ship ─────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FACTORY_KO="$REPO_ROOT/firmware/factory/bcmdhd.ko.jul2023"
PATCHED_KO="$REPO_ROOT/firmware/experimental/bcmdhd.ko.oct2025_mmc_sw_patched"

# ── SSH helper ─────────────────────────────────────────────────────
# Every tool accepts `--ip <address>` and defaults to USB-ethernet.
# Source this then call `parse_ip "$@"` to populate $IP and $SSH.
default_ip=169.254.100.100
IP="$default_ip"
parse_ip() {
    if [ "${1:-}" = "--ip" ] && [ -n "${2:-}" ]; then
        IP="$2"
    fi
}
# Re-parse once on source, using the caller's $@ passed as arguments.
parse_ip "$@"
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 pi@${IP}"
SCP="scp -q -o StrictHostKeyChecking=no"

# ── Pretty-print helpers (ANSI colors on TTYs only) ────────────────
if [ -t 1 ]; then
    _green="\033[32m" ; _red="\033[31m" ; _yel="\033[33m" ; _rst="\033[0m"
else
    _green="" ; _red="" ; _yel="" ; _rst=""
fi
pass() { printf "  ${_green}✓${_rst} %s\n" "$1"; }
fail() { printf "  ${_red}✗${_rst} %s\n" "$1"; }
warn() { printf "  ${_yel}!${_rst} %s\n" "$1"; }
info() { printf "    %s\n" "$1"; }
hr()   { printf "══════════════════════════════════════════════════════════════════\n"; }

# ── Driver md5 classification ──────────────────────────────────────
# Given an md5, echo one of: factory | patched | stock-wedges | unknown
classify_driver() {
    case "$1" in
        "$FACTORY_MD5")        echo factory ;;
        "$PATCHED_OCT25_MD5")  echo patched ;;
        "$STOCK_OCT25_MD5")    echo stock-wedges ;;
        *)                     echo unknown ;;
    esac
}

# ── Common preflight ───────────────────────────────────────────────
# Bail early if SSH isn't reachable.
require_ssh() {
    if ! $SSH 'true' 2>/dev/null; then
        fail "SSH to pi@${IP} failed. Check USB-ethernet / network path."
        exit 1
    fi
}
