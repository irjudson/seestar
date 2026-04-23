#!/bin/bash
# 9-point functional health check for a Seestar on any firmware.
#
# Accepts any of the three known driver states (factory Jul 2023,
# patched Oct 2025, stock Oct 2025) and flags the stock driver as the
# wedge-prone one. Other 8 checks exercise chip state, AP, hostapd,
# station mode, imager, sound-33 triggers, and JSON-RPC endpoints.
#
# Usage:
#   ./tools/verify_functional.sh [--ip 169.254.100.100]

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$REPO_ROOT/tools/lib/common.sh" "$@"

hr
echo "  Seestar functional check — target pi@${IP}"
hr
echo ""

# ── 1. Driver ─────────────────────────────────────────────────────
echo "[1] Driver check"
KO_INFO=$($SSH "md5sum $DRIVER_PATH; strings $DRIVER_PATH | grep 'compiled on' | head -1" 2>/dev/null)
KO_MD5=$(echo "$KO_INFO" | awk 'NR==1{print $1}')
KO_DATE=$(echo "$KO_INFO" | grep "compiled on" | sed 's/.*compiled on //')
case "$(classify_driver "$KO_MD5")" in
    factory)      pass "factory Jul 2023 driver ($KO_MD5, $KO_DATE)" ;;
    patched)      pass "patched Oct 2025 driver — mmc_hw_reset→mmc_sw_reset ($KO_MD5, $KO_DATE)" ;;
    stock-wedges) fail "STOCK Oct 2025 driver — known to wedge affected units ($KO_MD5, $KO_DATE)" ;;
    unknown)      fail "unknown driver variant — md5=$KO_MD5, date=$KO_DATE" ;;
esac

# ── 2. Firmware version ───────────────────────────────────────────
echo ""
echo "[2] Firmware version"
$SSH 'grep -E "^version_" /home/pi/ASIAIR/config' 2>/dev/null | sed 's/^/    /'

# ── 3. Chip state ─────────────────────────────────────────────────
echo ""
echo "[3] Chip state"
WLAN_STATE=$($SSH 'ip link show wlan0 2>/dev/null | head -1' | grep -oE '<[^>]+>' | head -1)
WL_COUNTRY=$($SSH 'sudo wl country 2>&1' | head -1)
HT_COUNT=$($SSH 'sudo dmesg -T | grep -c "HT Avail"' 2>/dev/null)
if echo "$WLAN_STATE" | grep -q "UP.*LOWER_UP"; then
    pass "wlan0 is $WLAN_STATE"
else
    fail "wlan0 state: $WLAN_STATE"
fi
if echo "$WL_COUNTRY" | grep -qvE "not found|Unsupported"; then
    pass "wl country: $WL_COUNTRY"
else
    fail "wl country: $WL_COUNTRY"
fi
if [ "$HT_COUNT" -lt 10 ]; then
    pass "HT Avail timeout count: $HT_COUNT (low)"
else
    fail "HT Avail timeout count: $HT_COUNT — chip is wedging"
fi

# ── 4. AP broadcasting ────────────────────────────────────────────
echo ""
echo "[4] AP (uap0) state"
UAP=$($SSH 'sudo iw dev uap0 info 2>&1' 2>/dev/null)
UAP_SSID=$(echo "$UAP" | grep -oE 'ssid [^[:space:]]+' | awk '{print $2}')
UAP_CHAN=$(echo "$UAP" | grep -oE 'channel [0-9]+' | awk '{print $2}')
UAP_TYPE=$(echo "$UAP" | grep -oE 'type [^[:space:]]+' | awk '{print $2}')
if [ "$UAP_TYPE" = "AP" ] && [ -n "$UAP_SSID" ]; then
    pass "uap0 broadcasting SSID=$UAP_SSID on channel $UAP_CHAN"
else
    fail "uap0 not in AP mode (type=$UAP_TYPE, ssid=$UAP_SSID)"
fi

# ── 5. hostapd ────────────────────────────────────────────────────
echo ""
echo "[5] hostapd.service"
HOSTAPD=$($SSH 'systemctl is-active hostapd.service 2>&1; systemctl show hostapd.service -p NRestarts --value 2>&1' 2>/dev/null)
HA_STATE=$(echo "$HOSTAPD" | head -1)
HA_RESTARTS=$(echo "$HOSTAPD" | tail -1)
if [ "$HA_STATE" = "active" ]; then
    if [ "${HA_RESTARTS:-0}" -lt 3 ]; then
        pass "hostapd.service active, restart count: $HA_RESTARTS"
    else
        fail "hostapd.service active but restart-looping ($HA_RESTARTS restarts)"
    fi
else
    fail "hostapd.service state: $HA_STATE"
fi

# ── 6. Station mode ───────────────────────────────────────────────
echo ""
echo "[6] Station mode"
WPA_SVR=$($SSH "grep wpa_svr $SH_CONF" 2>/dev/null)
if echo "$WPA_SVR" | grep -q "wpa_svr=1"; then
    STA_LINK=$($SSH 'sudo iw dev wlan0 link 2>&1' 2>/dev/null)
    if echo "$STA_LINK" | grep -q "Connected to"; then
        STA_SSID=$(echo "$STA_LINK" | grep -oE 'SSID: [^[:space:]]+' | head -1)
        pass "station associated ($STA_SSID)"
    else
        fail "wpa_svr=1 but station not associated"
        info "$STA_LINK"
    fi
else
    info "wpa_svr=0 (station mode disabled) — skipping"
fi

# ── 7. Imager process ─────────────────────────────────────────────
echo ""
echo "[7] zwoair_imager process"
IMAGER=$($SSH 'ps -ef | grep -v grep | grep -E "bin/zwoair_imager$" | head -1' 2>/dev/null)
if [ -n "$IMAGER" ]; then
    PID=$(echo "$IMAGER" | awk '{print $2}')
    pass "zwoair_imager running (PID $PID)"
else
    fail "zwoair_imager NOT running"
fi

# ── 8. Sound-33 loop ──────────────────────────────────────────────
echo ""
echo "[8] Sound-33 loop"
SND33=$($SSH 'sudo dmesg -T | grep -c "en33.wav\|wifi abnormal\|Escan set error"' 2>/dev/null)
if [ "$SND33" -eq 0 ]; then
    pass "no sound-33 triggers in dmesg"
else
    fail "$SND33 sound-33-related entries in dmesg"
fi

# ── 9. JSON-RPC endpoints ─────────────────────────────────────────
echo ""
echo "[9] JSON-RPC endpoints"
for port in 4700 4350 4361; do
    if timeout 3 bash -c "cat < /dev/null > /dev/tcp/${IP}/${port}" 2>/dev/null; then
        pass "port $port responding"
    else
        fail "port $port not responding"
    fi
done

echo ""
hr
