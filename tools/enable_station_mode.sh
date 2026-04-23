#!/bin/bash
# Enable station mode (wpa_svr=1) on the Seestar and trigger reassoc.
# Requires /etc/wpa_supplicant/wpa_supplicant.conf to already have home SSID creds.
#
# Usage: ./tools/enable_station_mode.sh [--ip 169.254.100.100]

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$REPO_ROOT/tools/lib/common.sh" "$@"

require_ssh

echo "[1/4] Current state:"
$SSH "grep wpa_svr $SH_CONF; ls -1 /etc/wpa_supplicant/ 2>/dev/null | head -5"

echo ""
echo "[2/4] Remount rw and flip wpa_svr to 1..."
$SSH "sudo mount -o remount,rw / && sudo sed -i 's/^wpa_svr=.*/wpa_svr=1/' $SH_CONF && grep wpa_svr $SH_CONF && sudo mount -o remount,ro /" || true

echo ""
echo "[3/4] Start wpa_supplicant / trigger reassoc..."
$SSH 'sudo /home/pi/ASIAIR/bin/network.sh connect 2>&1 | head -10' || true

echo ""
echo "[4/4] Station mode status (after 5s settle):"
sleep 5
$SSH 'sudo iw dev wlan0 link 2>&1 | head -5; echo ---; ip addr show wlan0 | grep inet' || true
