#!/bin/bash
# Seestar S50 recovery tool
#
# Usage:
#   ./seestar-recovery.sh                        Print current device state (no changes)
#   ./seestar-recovery.sh --pre-upgrade          Install license + configure WiFi before upgrade
#   ./seestar-recovery.sh --apply                Install license + configure WiFi after upgrade
#   ./seestar-recovery.sh --test-hostapd         Test new hostapd (channel=36 vs ACS) — diagnostic
#   ./seestar-recovery.sh --install-key          Copy SSH public key to device (one-time)
#   ./seestar-recovery.sh --ip <addr>            Override device IP (default: 10.0.0.1)
#   ./seestar-recovery.sh --firmware <dir>       Firmware package dir (used by --pre-upgrade and --test-hostapd)

set -e

DEVICE_IP="10.0.0.1"
DEVICE_USER="pi"
DEFAULT_PASS="raspberry"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o PasswordAuthentication=yes -o PubkeyAuthentication=yes"
TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
LICENSE_SRC="$TOOLS_DIR/../s50-fs/home/pi/.ZWO/zwoair_license"

# Home Wi-Fi network that the Seestar should re-join after upgrade.
# Source order:
#   1. $HOME/.seestar/home_wifi.env (preferred — sourced if present)
#   2. SEESTAR_HOME_SSID / SEESTAR_HOME_PSK env vars
#   3. Interactive prompt (last resort)
#
# home_wifi.env format:
#   SEESTAR_HOME_SSID="Your Network SSID"
#   SEESTAR_HOME_PSK="hex-psk-from-wpa_passphrase"
#
# Generate the hex PSK (so you don't embed the plaintext passphrase) with:
#   wpa_passphrase "Your Network SSID" "your-plaintext-passphrase" | grep '^\s*psk=' | cut -d= -f2
if [ -f "$HOME/.seestar/home_wifi.env" ]; then
    . "$HOME/.seestar/home_wifi.env"
fi
if [ -z "${SEESTAR_HOME_SSID:-}" ]; then
    read -r -p "Home Wi-Fi SSID for station mode: " SEESTAR_HOME_SSID
fi
if [ -z "${SEESTAR_HOME_PSK:-}" ]; then
    read -r -p "Home Wi-Fi WPA PSK (hex, from wpa_passphrase): " SEESTAR_HOME_PSK
fi
DESIRED_WPA="ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
	ssid=\"${SEESTAR_HOME_SSID}\"
	psk=${SEESTAR_HOME_PSK}
}
"

# ── mode parsing ──────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTION]

  (no args)            Print current device state — no changes made
  --pre-upgrade        Install license + configure station WiFi BEFORE upgrade.
                         Run while AP is working, then run the upgrade commands
                         printed at the end.
  --apply              Install license + configure station WiFi AFTER upgrade.
                         Run once the device is reachable (AP mode or station mode).
  --test-hostapd       Diagnostic: upload new hostapd from --firmware package,
                         test channel=36 vs channel=0/ACS with current driver,
                         then restore. SSH will drop briefly; script reconnects.
                         NOTE: This tests new hostapd against the CURRENT driver,
                         not necessarily the driver that ships with the firmware.
  --install-key        Copy SSH public key to device (one-time, uses password)
  --ip <addr>          Override device IP (default: $DEVICE_IP)
  --firmware <dir>     Firmware package directory (e.g. firmware/packages/fw_2.6.4)
  --help               Show this help

Pre-upgrade sequence:
  1. $(basename "$0") --install-key          (once, while on AP at 10.0.0.1)
  2. $(basename "$0") --pre-upgrade --firmware <dir>
       - installs license
       - asserts factory fixed AP channels (5G=36, 2.4G=11, autochannel_enabled=0)
         no-op on a fresh reflash; restores factory if something drifted
       - writes ${SEESTAR_HOME_SSID} wpa_supplicant.conf (home-net re-entry path)
       - LEAVES sh_conf.ccode EMPTY — this matches the known-working state.
         Empty ccode makes boot-time 'wl country' a no-op; hostapd's own
         country_code=us in AP_5G.conf sets the regulatory domain via nl80211.
       - prints exact scp+ssh upgrade commands
  3. Run the printed upgrade commands — device reboots
  4. Connect to SeestarS50 AP, then:
     $(basename "$0") --apply                (license + WiFi check after upgrade)

UART access (J2 pads, 1.8V logic, 1500000 baud):
  - Provides kernel boot output only — no login prompt (no getty configured).
EOF
}

MODE="status"
FIRMWARE_DIR=""

# Pre-scan for --ip and --firmware so they work in any position
args=("$@")
filtered=()
i=0
while [ $i -lt ${#args[@]} ]; do
    if [ "${args[$i]}" = "--ip" ]; then
        i=$((i+1))
        DEVICE_IP="${args[$i]:?--ip requires an address}"
    elif [ "${args[$i]}" = "--firmware" ]; then
        i=$((i+1))
        FIRMWARE_DIR="${args[$i]:?--firmware requires a directory}"
    else
        filtered+=("${args[$i]}")
    fi
    i=$((i+1))
done
set -- "${filtered[@]+"${filtered[@]}"}"

case "${1:-}" in
    --pre-upgrade)    MODE="pre-upgrade" ;;
    --apply)          MODE="apply" ;;
    --test-hostapd)   MODE="test-hostapd" ;;
    --test-nvram)     MODE="test-nvram" ;;
    --test-nvram-file) MODE="test-nvram-file" ;;
    --install-key)    MODE="install-key" ;;
    --help|-h)        usage; exit 0 ;;
    "")               MODE="status" ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
esac

# ── helpers ───────────────────────────────────────────────────────────────────
ssh_run() { ssh $SSH_OPTS ${DEVICE_USER}@${DEVICE_IP} "$@"; }
scp_to()  { scp $SSH_OPTS "$1" ${DEVICE_USER}@${DEVICE_IP}:"$2"; }
step()    { echo ""; echo "==> $*"; }
ok()      { echo "    [OK] already correct — no change"; }
changed() { echo "    [CHANGED] $*"; }
info()    { echo "    $*"; }
show_value() { printf "  %-38s %s\n" "$1" "$2"; }

# ── SSH key install mode ──────────────────────────────────────────────────────
if [ "$MODE" = "install-key" ]; then
    echo ""
    echo "Seestar S50 Recovery Tool  [mode: install-key]"
    echo "Installing SSH public key on device (password will be required once)."
    echo ""
    PUBKEY=""
    for candidate in ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub ~/.ssh/id_ecdsa.pub; do
        if [ -f "$candidate" ]; then PUBKEY="$candidate"; break; fi
    done
    if [ -z "$PUBKEY" ]; then
        echo "No SSH public key found in ~/.ssh/. Generate one with: ssh-keygen -t ed25519"
        exit 1
    fi
    echo "Using key: $PUBKEY"
    if command -v sshpass >/dev/null 2>&1; then
        sshpass -p "$DEFAULT_PASS" ssh-copy-id $SSH_OPTS -i "$PUBKEY" ${DEVICE_USER}@${DEVICE_IP}
    else
        echo "sshpass not found — falling back to ssh-copy-id (will prompt for password: $DEFAULT_PASS)"
        ssh-copy-id $SSH_OPTS -i "$PUBKEY" ${DEVICE_USER}@${DEVICE_IP}
    fi
    echo ""
    echo "Key installed. Future runs will not require a password."
    # Fall through into the status block below so the user sees device state.
    MODE="status"
fi

# ── connectivity check ────────────────────────────────────────────────────────
echo ""
echo "Seestar S50 Recovery Tool  [mode: $MODE]"
echo "Connecting to ${DEVICE_USER}@${DEVICE_IP}..."
if ! ssh_run true 2>/dev/null; then
    echo "ERROR: Cannot reach device at $DEVICE_IP"
    echo "Make sure you are connected to the SeestarS50 AP"
    echo "If this is your first run, try: $0 --install-key"
    exit 1
fi
echo "Connected."

# ═════════════════════════════════════════════════════════════════════════════
# CURRENT STATE — always printed
# ═════════════════════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════ CURRENT STATE ════════════════════════"

FW_VER=$(ssh_run "grep '^version_string=' /home/pi/ASIAIR/config 2>/dev/null | cut -d= -f2" || true)
FW_INT=$(ssh_run "grep '^version_int=' /home/pi/ASIAIR/config 2>/dev/null | cut -d= -f2" || true)
show_value "firmware version:" "${FW_VER:-'(unknown)'}  (version_int=${FW_INT:-'?'})"

DEVICE_MD5=$(ssh_run "md5sum /home/pi/.ZWO/zwoair_license 2>/dev/null | awk '{print \$1}'" || true)
if [ -z "$DEVICE_MD5" ]; then
    show_value "license:" "(not present)"
else
    LOCAL_MD5=$(md5sum "$LICENSE_SRC" 2>/dev/null | awk '{print $1}' || true)
    if [ "$DEVICE_MD5" = "$LOCAL_MD5" ]; then
        show_value "license md5:" "$DEVICE_MD5  [matches local]"
    else
        show_value "license md5:" "$DEVICE_MD5  [differs from local: ${LOCAL_MD5:-no local file}]"
    fi
fi

DPKG_ASIAIR=$(ssh_run 'dpkg -s asiair 2>/dev/null | grep "^Version:" || echo "(not registered)"')
show_value "dpkg asiair:" "$DPKG_ASIAIR"

CURRENT_CONF=$(ssh_run 'cat /home/pi/.ZWO/sh_conf.txt 2>/dev/null || true')
WPA_SVR_NOW=$(echo "$CURRENT_CONF" | grep '^wpa_svr=' | head -1 || true)
CCODE_NOW=$(echo "$CURRENT_CONF"   | grep '^ccode='   | head -1 || true)
show_value "sh_conf.txt  wpa_svr:" "${WPA_SVR_NOW:-'(missing)'}"
CCODE_STATUS="${CCODE_NOW:-'(missing — wl country will NOT run at boot)'}"
show_value "sh_conf.txt  ccode:"   "$CCODE_STATUS"

NVRAM_CC=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
NVRAM_SET=$(echo "${CCODE_NOW:-}" | cut -d= -f2)
if [ -z "$NVRAM_CC" ]; then
    show_value "BCM NVRAM country:" "(unknown — 'wl country' unavailable)"
elif [ -n "$NVRAM_SET" ] && [ "$NVRAM_SET" != "$NVRAM_CC" ]; then
    show_value "BCM NVRAM country:" "$NVRAM_CC  [MISMATCH with sh_conf.ccode=$NVRAM_SET → boot will run wl country and break AP]"
else
    show_value "BCM NVRAM country:" "$NVRAM_CC  [matches sh_conf → boot will skip wl country]"
fi

AP5_CH=$(ssh_run  "grep '^channel=' /home/pi/AP_5G.conf 2>/dev/null || true")
AP5_ACS=$(ssh_run "grep '^autochannel_enabled=' /home/pi/AP_5G.conf 2>/dev/null || true")
AP24_CH=$(ssh_run  "grep '^channel=' /home/pi/AP_2.4G.conf 2>/dev/null || true")
AP24_ACS=$(ssh_run "grep '^autochannel_enabled=' /home/pi/AP_2.4G.conf 2>/dev/null || true")
show_value "AP_5G.conf:"   "${AP5_CH:-'(missing)'}  ${AP5_ACS}"
show_value "AP_2.4G.conf:" "${AP24_CH:-'(missing)'}  ${AP24_ACS}"

AP_SSID=$(ssh_run "grep '^ssid=' /home/pi/AP_5G.conf 2>/dev/null | head -1" || true)
DEV_SERIAL=$(ssh_run "grep -i '^Serial' /proc/cpuinfo 2>/dev/null | awk '{print \$NF}'" || true)
DEV_SERIAL_TAIL=${DEV_SERIAL: -8}
AP_ID_INITED=$(ssh_run "grep -o '>true</ap_id_inited>\\|>false</ap_id_inited>' /home/pi/.ZWO/ASIAIR_general.xml 2>/dev/null | head -1" || true)
AP_ID_STATE="${AP_ID_INITED#>}"; AP_ID_STATE="${AP_ID_STATE%</ap_id_inited>}"
show_value "AP SSID  (AP_5G.conf):" "${AP_SSID:-'(missing)'}"
if [ -n "$DEV_SERIAL_TAIL" ]; then
    if echo "$AP_SSID" | grep -qi "$DEV_SERIAL_TAIL"; then
        show_value "SSID matches CPU serial:" "yes ($DEV_SERIAL_TAIL)"
    else
        show_value "SSID matches CPU serial:" "NO — device serial is $DEV_SERIAL_TAIL, SSID shows otherwise (donor image?)"
    fi
fi
show_value "ap_id_inited:" "${AP_ID_STATE:-'(missing)'} ${AP_ID_STATE:+(false → zwoair_imager regens SSID on next boot)}"

SSIDS=$(ssh_run "grep '^\s*ssid=' /home/pi/wpa_supplicant.conf 2>/dev/null | sed 's/.*ssid=//' | tr '\n' ' '" || true)
COUNTRY_NOW=$(ssh_run "grep '^country=' /home/pi/wpa_supplicant.conf 2>/dev/null || true")
show_value "wpa_supplicant  country:" "${COUNTRY_NOW:-'(missing)'}"
show_value "wpa_supplicant  networks:" "${SSIDS:-'(none)'}"

# Firmware upgrade recommendation
# KNOWN-SAFE endpoint is fw_2.6.1 (5.50). Upgrades past 5.50 into the 5.82+
# range wedge the WiFi chip with HT Avail timeout; recovery requires a full
# rkdeveloptool reflash. See UPGRADE_PROBLEM_SUMMARY.md.
AVAIL_FW=$(ls -1d "$TOOLS_DIR/../firmware/packages"/fw_* 2>/dev/null | sort -V || true)
SAFE_FW="$TOOLS_DIR/../firmware/packages/fw_2.6.1"
NEXT_UNTESTED_FW="$TOOLS_DIR/../firmware/packages/fw_2.6.4"
if [ -n "$AVAIL_FW" ]; then
    LATEST_FW=$(echo "$AVAIL_FW" | tail -1)
    LATEST_VER=$(basename "$LATEST_FW" | sed 's/^fw_//')
    show_value "available: safe target:" "fw_2.6.1 (5.50) ← last known-good"
    show_value "          next-untested:" "fw_2.6.4 (5.82) ← country-prime hypothesis not yet tested"
    show_value "          latest in repo:" "$LATEST_VER (risk: wedges chip without proven recovery path)"
fi

echo "════════════════════════════════════════════════════════════════"

if [ "$MODE" = "status" ]; then
    echo ""
    case "${FW_VER:-unknown}" in
        5.50|2550)
            echo "Device is on 5.50 (known-good). Only upgrade if you want to test"
            echo "the untested country-prime hypothesis on 5.82 — prepared to"
            echo "recover via rkdeveloptool reflash if the chip wedges. See"
            echo "UPGRADE_PROBLEM_SUMMARY.md."
            echo ""
            echo "Pre-upgrade prep for 5.82 (if you're going to try):"
            echo "  $(basename "$0") --pre-upgrade --firmware $NEXT_UNTESTED_FW"
            ;;
        5.82|2582|5.97|2597|6.45|2645|6.70|2670|7.06|2706|7.18|2718|7.32|2732)
            echo "Device is on $FW_VER (past the known-good endpoint)."
            echo "If WiFi works, stay here. If it doesn't, downgrade via rkdeveloptool."
            ;;
        *)
            echo "Status only — no changes made."
            ;;
    esac
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS — license and WiFi config used by both pre-upgrade and apply
# ═════════════════════════════════════════════════════════════════════════════
do_license() {
    # Install license via pi_encrypt JSON-RPC (port 4700) — same server-side
    # handler the vendor APK invokes through BLE's send_to_air_reply wrapper.
    # Verify via pi_is_verified afterward. Falls back to SCP if the RPC
    # isn't implemented (very old firmware) or fails.
    step "License file (via pi_encrypt JSON-RPC, same as vendor BLE path)"
    if [ ! -f "$LICENSE_SRC" ]; then
        echo "ERROR: License source not found: $LICENSE_SRC"
        echo "       Generate one with: python3 tools/get_license.py --out $LICENSE_SRC"
        exit 1
    fi
    LOCAL_MD5=$(md5sum "$LICENSE_SRC" | awk '{print $1}')
    if [ "$DEVICE_MD5" = "$LOCAL_MD5" ]; then
        ok
        # Even if file md5 matches, re-verify via RPC (it's cheap and catches
        # cases where the file was written but the device's in-memory state
        # didn't pick it up).
        if python3 "$TOOLS_DIR/install_license_rpc.py" --host "$DEVICE_IP" \
                --license-file "$LICENSE_SRC" --verify-only >/dev/null 2>&1; then
            info "pi_is_verified: true"
        fi
        return
    fi

    info "Installing license (device had: ${DEVICE_MD5:-missing}, local: $LOCAL_MD5)"
    info "Calling pi_encrypt JSON-RPC on $DEVICE_IP:4700..."
    RPC_OUT=$(python3 "$TOOLS_DIR/install_license_rpc.py" --host "$DEVICE_IP" \
              --license-file "$LICENSE_SRC" 2>&1)
    RPC_RC=$?
    echo "$RPC_OUT" | sed 's/^/    /'
    if [ $RPC_RC -eq 0 ]; then
        changed "license installed via pi_encrypt + verified via pi_is_verified"
        return
    fi

    # RPC path failed (method not found / firmware too old / network issue).
    # Fall back to SCP so we're still functional on 2.42 if pi_encrypt is
    # absent.
    info "pi_encrypt RPC failed (rc=$RPC_RC); falling back to SCP to /home/pi/.ZWO/"
    ssh_run "mkdir -p /home/pi/.ZWO"
    scp $SSH_OPTS "$LICENSE_SRC" ${DEVICE_USER}@${DEVICE_IP}:/home/pi/.ZWO/zwoair_license
    changed "license installed via SCP fallback"
}

do_ccode_us() {
    # Stock vendor mechanism: reload_country("US") in network.sh writes
    # ccode=US to sh_conf.txt. On every boot on fw_2.6.4+, asiair.sh's block
    # reads ccode=US, sees driver reports CN, fires `wl country US`, regdom
    # set to US before hostapd restart. This is how a normal app-set-up
    # device works. NVRAM doesn't persist across reboot (proven), so the
    # boot-time call is load-bearing — ccode=US in sh_conf.txt makes it fire.
    # On fw_2.6.1/5.50 and older, asiair.sh has no such block, so this is
    # inert; it only activates after upgrade to fw_2.6.4+.
    step "sh_conf.txt — ccode=US (triggers asiair.sh boot block on 2.6.4+)"
    local cur
    cur=$(ssh_run "grep '^ccode=' /home/pi/.ZWO/sh_conf.txt 2>/dev/null || true")
    if [ "$cur" = "ccode=US" ]; then
        ok
    else
        info "Was: ${cur:-'(missing)'}"
        ssh_run "grep -q '^ccode=' /home/pi/.ZWO/sh_conf.txt \
            && sudo sed -i 's/^ccode=.*/ccode=US/' /home/pi/.ZWO/sh_conf.txt \
            || echo 'ccode=US' | sudo tee -a /home/pi/.ZWO/sh_conf.txt > /dev/null"
        changed "ccode=US written"
    fi
}

do_reset_ap_id() {
    # Force zwoair_imager to regenerate the AP SSID from THIS device's own
    # /proc/cpuinfo serial on next boot. Without this, a reflash from a donor
    # seestarOS.img leaves the donor's SSID (e.g. S50_3731a279) baked into
    # AP_5G.conf / AP_2.4G.conf, and ap_id_inited=true in ASIAIR_general.xml
    # tells zwoair_imager to leave it alone. Flipping the flag to false makes
    # zwoair_imager run its pi_reset_ap_id_passwd routine on next boot →
    # ssid=S50_<your_cpu_serial> ends up in both AP conf files.
    step "ASIAIR_general.xml — ap_id_inited=false (force SSID regen from this device's serial)"
    local xml="/home/pi/.ZWO/ASIAIR_general.xml"
    local cur
    cur=$(ssh_run "grep -o '>true</ap_id_inited>\\|>false</ap_id_inited>' $xml 2>/dev/null | head -1" || true)
    if [ -z "$cur" ]; then
        info "$xml: (not present or no ap_id_inited field) — skipping"
        ok
        return
    fi
    if [ "$cur" = ">false</ap_id_inited>" ]; then
        info "ap_id_inited already false — zwoair_imager will regen SSID on next boot"
        ok
        return
    fi
    info "ap_id_inited=true → flipping to false"
    ssh_run "sudo sed -i 's|>true</ap_id_inited>|>false</ap_id_inited>|g' $xml"
    # Also flip /root/.ZWO/ copy if present (zwoair_imager running as root reads this one).
    ssh_run "[ -f /root/.ZWO/ASIAIR_general.xml ] && sudo sed -i 's|>true</ap_id_inited>|>false</ap_id_inited>|g' /root/.ZWO/ASIAIR_general.xml || true"
    changed "ap_id_inited=false (SSID will regenerate to S50_<your-cpu-serial> on next boot)"
}

do_en_eth() {
    # /home/pi/en_eth marker — toggles the USB gadget from default mass_storage
    # to g_ether (169.254.100.100). Read by /etc/usb_gadgets.sh (or equivalent
    # factory boot logic). Without this file, USB-C comes up as a USB disk and
    # there's no ethernet fallback when WiFi breaks. Baseline-2.42 rkdeveloptool
    # images don't ship it, so it must be re-created after any full reflash.
    step "/home/pi/en_eth — enable USB-ethernet gadget mode"
    if ssh_run "[ -f /home/pi/en_eth ]"; then
        ok
    else
        info "Missing — creating marker"
        ssh_run "touch /home/pi/en_eth"
        changed "/home/pi/en_eth created (USB comes up as ethernet on next boot)"
    fi
}

do_wpa_svr() {
    # Force station mode on boot so the device joins ${SEESTAR_HOME_SSID} on
    # home WiFi. If the AP fails to come up after upgrade, this gives us a
    # back-channel to SSH in and diagnose (instead of another reflash).
    step "sh_conf.txt — wpa_svr=1 (station mode back-channel)"
    local cur
    cur=$(ssh_run "grep '^wpa_svr=' /home/pi/.ZWO/sh_conf.txt 2>/dev/null || true")
    if [ "$cur" = "wpa_svr=1" ]; then
        ok
    else
        info "Was: ${cur:-'(missing)'}"
        ssh_run "grep -q '^wpa_svr=' /home/pi/.ZWO/sh_conf.txt \
            && sudo sed -i 's/^wpa_svr=.*/wpa_svr=1/' /home/pi/.ZWO/sh_conf.txt \
            || echo 'wpa_svr=1' | sudo tee -a /home/pi/.ZWO/sh_conf.txt > /dev/null"
        changed "wpa_svr=1 written (station mode will start on next boot)"
    fi
}

do_ap_conf() {
    # Enforce the FACTORY fixed-channel AP config.
    # hostapd ignores `autochannel_enabled` (ZWO-script metadata); what matters is
    # `channel=`. Fixed channels avoid the ACS scan path that triggers escan -43
    # on the post-2.6.4 driver state. 36 is US/UNII-1 (no DFS), 11 is US 2.4 GHz.
    # Only REWRITE existing fields; never ADD fields. Old plain hostapd (fw_≤2.6.1)
    # doesn't recognize `autochannel_enabled` — appending it to a factory AP conf
    # that doesn't already have it causes hostapd to reject the whole config and
    # the AP never comes up. The new hostapd (fw_2.6.4+ v2.8.20250701.ACS) adds
    # the line itself when needed.
    step "AP conf — assert factory fixed channels (5G=36, 2.4G=11) if drifted"
    _set_fixed() {
        local conf="$1" want_ch="$2"
        local cur_ch cur_acs
        cur_ch=$(ssh_run  "grep '^channel=' $conf 2>/dev/null || true")
        cur_acs=$(ssh_run "grep '^autochannel_enabled=' $conf 2>/dev/null || true")
        if [ "$cur_ch" = "channel=$want_ch" ]; then
            info "$conf: channel already $want_ch ${cur_acs:+($cur_acs)}"
        else
            info "$conf: was $cur_ch  ${cur_acs:-'(no autochannel_enabled line)'}"
            ssh_run "sudo sed -i 's/^channel=.*/channel=$want_ch/' $conf"
            changed "$conf → channel=$want_ch"
        fi
        # Only flip autochannel_enabled to 0 if a line ALREADY exists. Do not add.
        if [ -n "$cur_acs" ] && [ "$cur_acs" != "autochannel_enabled=0" ]; then
            ssh_run "sudo sed -i 's/^autochannel_enabled=.*/autochannel_enabled=0/' $conf"
            changed "$conf → autochannel_enabled=0 (existing line rewritten)"
        fi
    }
    _set_fixed /home/pi/AP_5G.conf   36
    _set_fixed /home/pi/AP_2.4G.conf 11
}

do_country_us() {
    # Run the VENDOR's own reload_country via network.sh. Only present on fw_2.6.4+.
    # Vendor sequence: stop hostapd → set ccode=US → wl country US → add
    # autochannel_enabled=1 to AP_{5G,2.4G}.conf → start hostapd. Because hostapd
    # is DOWN while the config is being rewritten, even a hostapd that would
    # reject autochannel_enabled never reads the intermediate file.
    step "network.sh country US — vendor reload_country flow"
    local has_country_cmd
    has_country_cmd=$(ssh_run "grep -q '\"\$1\" = \"country\"' /home/pi/ASIAIR/bin/network.sh && echo yes || echo no" 2>/dev/null || echo "no")
    if [ "$has_country_cmd" != "yes" ]; then
        info "network.sh lacks 'country' subcommand (fw_<2.6.4) — skipping"
        ok
        return
    fi
    local cur_ccode cur_nvram
    cur_ccode=$(ssh_run "grep '^ccode=' /home/pi/.ZWO/sh_conf.txt 2>/dev/null | cut -d= -f2" || true)
    cur_nvram=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    if [ "$cur_ccode" = "US" ] && [ "$cur_nvram" = "US" ]; then
        info "Already ccode=US + NVRAM=US — vendor reload_country not needed"
        ok
        return
    fi
    info "Before: sh_conf.ccode=${cur_ccode:-empty}, NVRAM=${cur_nvram:-empty}"
    info "Running: sudo /home/pi/ASIAIR/bin/network.sh country US"
    info "(stops hostapd briefly; SSH may drop if on SeestarS50 AP — script waits then verifies)"
    ssh_run "sudo /home/pi/ASIAIR/bin/network.sh country US" || true

    # reload_country runs in background (& in vendor code). Wait and reconnect.
    info "Waiting for reload_country to settle (up to 45s)..."
    local i
    for i in $(seq 1 9); do
        sleep 5
        if ssh $SSH_OPTS ${DEVICE_USER}@${DEVICE_IP} true 2>/dev/null; then
            info "reachable after ${i}x5s"
            break
        fi
    done

    local new_ccode new_nvram new_acs5 new_acs24
    new_ccode=$(ssh_run "grep '^ccode=' /home/pi/.ZWO/sh_conf.txt 2>/dev/null | cut -d= -f2" || true)
    new_nvram=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    new_acs5=$(ssh_run  "grep '^autochannel_enabled=' /home/pi/AP_5G.conf   2>/dev/null" || true)
    new_acs24=$(ssh_run "grep '^autochannel_enabled=' /home/pi/AP_2.4G.conf 2>/dev/null" || true)
    if [ "$new_ccode" = "US" ] && [ "$new_nvram" = "US" ] \
        && [ "$new_acs5" = "autochannel_enabled=1" ] && [ "$new_acs24" = "autochannel_enabled=1" ]; then
        changed "vendor reload_country completed: ccode=US, NVRAM=US, autochannel_enabled=1 on both AP files"
    else
        echo "    WARNING: partial result — ccode=$new_ccode, NVRAM=$new_nvram, 5G=$new_acs5, 2.4G=$new_acs24"
        echo "    Inspect manually: ssh pi@${DEVICE_IP} 'sudo wl country; cat /home/pi/.ZWO/sh_conf.txt'"
    fi
}

do_wifi() {
    step "wpa_supplicant.conf — ${SEESTAR_HOME_SSID} (station)"
    CURRENT_WPA=$(ssh_run 'cat /home/pi/wpa_supplicant.conf 2>/dev/null || true')
    if [ "$CURRENT_WPA" = "$DESIRED_WPA" ]; then
        ok
    else
        info "Was networks: $SSIDS  country: $COUNTRY_NOW"
        ssh_run "sudo sh -c 'cat > /home/pi/wpa_supplicant.conf'" <<'EOF'
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
	ssid="${SEESTAR_HOME_SSID}"
	psk=7a1818f2bd1f56f55a3655c093e708c42db096601b4982f06d2832f8d343d3d9
}
EOF
        changed "${SEESTAR_HOME_SSID} only, country=US"
    fi
}

# ═════════════════════════════════════════════════════════════════════════════
# PRE-UPGRADE MODE
# ═════════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "pre-upgrade" ]; then
    echo ""
    echo "════════════════════════ PRE-UPGRADE ═══════════════════════════"

    do_license
    do_wifi
    # do_wpa_svr DISABLED for 5.82 upgrade — wpa_supplicant starting concurrently
    # with hostapd at boot appears to trigger escan-43 → zwoair_imager RestartWifi
    # loop → sound 33. Stock factory default is wpa_svr=0 (app sets it to 1 only
    # after station mode is explicitly configured). Match stock.
    do_ccode_us
    do_ap_conf
    do_reset_ap_id
    do_en_eth

    if [ -z "$FIRMWARE_DIR" ]; then
        FW_PKGS=$(ls -1d "$TOOLS_DIR/../firmware/packages"/fw_* 2>/dev/null | sort -V || true)
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo ""
        echo "Device is ready. Re-run with --firmware to get upgrade commands:"
        if [ -n "$FW_PKGS" ]; then
            echo "  Available packages:"
            echo "$FW_PKGS" | while read -r d; do echo "    $d"; done
            LATEST=$(echo "$FW_PKGS" | tail -1)
            echo ""
            echo "  $(basename "$0") --pre-upgrade --firmware $LATEST"
        else
            echo "  $(basename "$0") --pre-upgrade --firmware firmware/packages/fw_X.Y.Z"
        fi
    else
        FW_DIR_ABS="$(cd "$FIRMWARE_DIR" && pwd)"
        if [ ! -f "$FW_DIR_ABS/update_package.sh" ]; then
            echo "ERROR: $FW_DIR_ABS/update_package.sh not found — is this a valid firmware package?"
            exit 1
        fi
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo ""
        echo "Device is ready. Run these commands to upgrade:"
        echo ""
        echo "  scp -r \"$FW_DIR_ABS\" ${DEVICE_USER}@${DEVICE_IP}:/tmp/fw_update"
        echo "  ssh ${DEVICE_USER}@${DEVICE_IP} 'cd /tmp/fw_update && sudo bash update_package.sh'"
        echo ""
        echo "The device will reboot automatically."
        echo "AP should come up on the SeestarS50 network after reboot."
        echo "Then connect and run: $(basename "$0") --apply --ip 10.0.0.1"
    fi
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# APPLY MODE
# ═════════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "apply" ]; then
    echo ""
    echo "════════════════════════ APPLY ════════════════════════════════"

    do_license
    do_wifi
    do_country_us
    do_reset_ap_id
    do_en_eth

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Done."
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# TEST-NVRAM MODE
# Does `wl country US` persist in the BCM chip NVRAM across a full reboot?
# Sequence: stop hostapd → wl country US → verify → start hostapd → reboot →
# reconnect → query wl country. If still US, pre-priming on fw_2.6.1 is a
# viable strategy for 5.82+ upgrades. If it reverts, we need a different fix.
# ═════════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "test-nvram" ]; then
    echo ""
    echo "════════════════════════ TEST NVRAM PERSISTENCE ════════════════════════"

    step "1. Record current NVRAM country"
    BEFORE=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    info "Before: ${BEFORE:-'(empty)'}"
    if [ -z "$BEFORE" ]; then
        info "wl command unavailable — cannot run test"
        exit 1
    fi

    step "2. Set wl country US (vendor-safe sequence: stop hostapd first)"
    ssh_run "sudo systemctl stop hostapd.service" || true
    sleep 1
    ssh_run "sudo wl country US" || true
    sleep 1
    MID=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    info "After wl country US: ${MID:-'(empty)'}"
    if [ "$MID" != "US" ]; then
        echo "    ERROR: wl country US did not take effect even at runtime."
        ssh_run "sudo systemctl start hostapd.service" || true
        exit 1
    fi

    step "3. Restart hostapd so AP stays up across the upcoming reboot transition"
    ssh_run "sudo systemctl start hostapd.service" || true

    step "4. Reboot the device (SSH will drop)"
    ssh_run "sudo nohup sh -c 'sleep 2; reboot' > /dev/null 2>&1 &" || true
    info "Reboot initiated. Waiting up to 3 minutes for SSH to come back..."

    # Wait for SSH to drop then come back
    sleep 10
    RECONNECTED=0
    for i in $(seq 1 30); do
        sleep 5
        printf "    attempt %2d/30 (%3ds elapsed)... " "$i" "$((10 + i*5))"
        if ssh $SSH_OPTS ${DEVICE_USER}@${DEVICE_IP} true 2>/dev/null; then
            echo "reconnected."
            RECONNECTED=1
            break
        else
            echo "not yet"
        fi
    done

    if [ "$RECONNECTED" -eq 0 ]; then
        echo ""
        echo "ERROR: device did not come back in 3 minutes."
        echo "       Check manually: ssh pi@${DEVICE_IP}"
        exit 1
    fi

    step "5. Post-reboot NVRAM readback — THE TEST"
    AFTER=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    info "Before test: ${BEFORE}"
    info "After reboot: ${AFTER:-'(empty)'}"
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    if [ "$AFTER" = "US" ]; then
        echo "  RESULT: NVRAM PERSISTED → pre-priming on fw_2.6.1 IS a viable strategy"
        echo "          for the 5.82+ upgrade path (avoids the boot-time wl country block)"
    else
        echo "  RESULT: NVRAM REVERTED ($BEFORE → US → $AFTER)"
        echo "          wl country is runtime-only; pre-priming does NOT survive reboot."
        echo "          Need a different approach (modprobe option, clm_blob, or systemd unit)."
    fi
    echo "════════════════════════════════════════════════════════════════════════"
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# TEST-NVRAM-FILE MODE
# Edit /usr/lib/firmware/nvram_ap6275s.txt to change ccode=0 → ccode=US, then
# reboot. If wl country returns US post-boot WITHOUT any runtime call, we've
# found the persistent country-code setting. This file is the bcmdhd driver's
# NVRAM defaults loaded at module probe time. Our upgrade path's update_package.sh
# doesn't replace it, so a single edit survives fw_2.6.4 upgrade.
# Mode is reversible: records the original file, restores on failure.
# ═════════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "test-nvram-file" ]; then
    echo ""
    echo "════════════════════════ TEST NVRAM FILE PERSISTENCE ════════════════════════"
    NVRAM=/usr/lib/firmware/nvram_ap6275s.txt
    BAK=/home/pi/nvram_ap6275s.txt.bak

    step "1. Read current ccode/regrev from $NVRAM"
    BEFORE_CCODE=$(ssh_run "grep '^ccode=' $NVRAM 2>/dev/null" || true)
    BEFORE_REGREV=$(ssh_run "grep '^regrev=' $NVRAM 2>/dev/null" || true)
    info "Before: ${BEFORE_CCODE:-'(no ccode line)'}  ${BEFORE_REGREV:-'(no regrev)'}"

    step "2. Backup, then patch ccode=US"
    ssh_run "[ -f $BAK ] || sudo cp $NVRAM $BAK"
    info "Backup at $BAK on device"
    ssh_run "sudo mount -o remount,rw / 2>/dev/null; sudo sed -i 's/^ccode=.*/ccode=US/' $NVRAM; sync; sudo mount -o remount,ro / 2>/dev/null" || true
    AFTER_CCODE=$(ssh_run "grep '^ccode=' $NVRAM 2>/dev/null" || true)
    info "Patched: $AFTER_CCODE"
    if [ "$AFTER_CCODE" != "ccode=US" ]; then
        echo "    ERROR: sed did not take effect. $NVRAM might be on read-only mount."
        exit 1
    fi

    step "3. Record runtime wl country BEFORE reboot (should still be old value)"
    PRE_RUNTIME=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    info "Runtime wl country: ${PRE_RUNTIME:-'(empty)'} (will be re-read by driver on next module load)"

    step "4. Reboot (SSH will drop)"
    ssh_run "sudo nohup sh -c 'sleep 2; reboot' > /dev/null 2>&1 &" || true
    info "Reboot initiated. Waiting up to 3 minutes for SSH to come back..."
    sleep 10
    RECONNECTED=0
    for i in $(seq 1 30); do
        sleep 5
        printf "    attempt %2d/30 (%3ds)... " "$i" "$((10 + i*5))"
        if ssh $SSH_OPTS ${DEVICE_USER}@${DEVICE_IP} true 2>/dev/null; then
            echo "reconnected."
            RECONNECTED=1
            break
        else
            echo "not yet"
        fi
    done
    if [ "$RECONNECTED" -eq 0 ]; then
        echo "ERROR: device did not come back. Try a hard reboot. Backup is at $BAK on device."
        exit 1
    fi

    step "5. Post-reboot wl country readback — THE TEST"
    POST=$(ssh_run "sudo wl country 2>/dev/null | awk '{print \$1}'" || true)
    info "After reboot: ${POST:-'(empty)'}"
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    if [ "$POST" = "US" ]; then
        echo "  RESULT: NVRAM FILE PERSISTED — driver boots with US regdom!"
        echo "          This is the mechanism. Pre-upgrade edit of nvram_ap6275s.txt"
        echo "          will survive the 5.82+ firmware upgrade and prime the regdom"
        echo "          before hostapd starts, avoiding the escan-43 false positive."
        echo ""
        echo "  To revert: ssh pi@${DEVICE_IP} 'sudo mount -o remount,rw /; sudo cp $BAK $NVRAM; sync; sudo mount -o remount,ro /; sudo reboot'"
    else
        echo "  RESULT: driver did NOT adopt ccode=US from nvram file (got: $POST)"
        echo "          Either the driver ignores ccode, or regrev matters, or there's"
        echo "          another NVRAM source overriding. Reverting via:"
        echo "          ssh pi@${DEVICE_IP} 'sudo mount -o remount,rw /; sudo cp $BAK $NVRAM; sync; sudo mount -o remount,ro /'"
    fi
    echo "═══════════════════════════════════════════════════════════════════════════════"
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# TEST-HOSTAPD MODE
# Tests new hostapd from --firmware package against the CURRENTLY LOADED driver.
# NOTE: This does NOT test the new bcmdhd.ko — only the hostapd binary changes.
#       Results reflect new hostapd + current driver, not the post-upgrade combo.
# ═════════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "test-hostapd" ]; then
    echo ""
    echo "════════════════════════ TEST HOSTAPD ════════════════════════"

    if [ -z "$FIRMWARE_DIR" ]; then
        echo "ERROR: --firmware <dir> required for --test-hostapd"
        echo "  e.g. $(basename "$0") --test-hostapd --firmware firmware/packages/fw_2.6.4"
        exit 1
    fi
    NEW_HOSTAPD_SRC="$FIRMWARE_DIR/others/hostapd"
    if [ ! -f "$NEW_HOSTAPD_SRC" ]; then
        echo "ERROR: hostapd not found at: $NEW_HOSTAPD_SRC"
        exit 1
    fi

    step "1. Upload new hostapd binary to device"
    scp_to "$NEW_HOSTAPD_SRC" /tmp/hostapd_new
    ssh_run "chmod +x /tmp/hostapd_new"
    NEW_VER=$(ssh_run "/tmp/hostapd_new -v 2>&1 | head -1 || true")
    OLD_VER=$(ssh_run "hostapd -v 2>&1 | head -1 || true")
    info "New binary: $NEW_VER"
    info "Current:    $OLD_VER"
    info "Driver:     $(ssh_run 'modinfo bcmdhd 2>/dev/null | grep ^version | head -1 || echo unknown')"

    step "2. Write self-contained test script to device"
    ssh_run "cat > /tmp/run_hostapd_test.sh" << 'REMOTE_SCRIPT'
#!/bin/bash
LOG=/tmp/hostapd_test_results.log
AP_CONF=/home/pi/AP_5G.conf
TMP_CONF=/tmp/hostapd_test.conf
NEW=/tmp/hostapd_new

echo "=== hostapd channel test ===" > "$LOG"
echo "New binary: $($NEW -v 2>&1 | head -1)" >> "$LOG"
echo "Driver: $(modinfo bcmdhd 2>/dev/null | grep ^version | head -1 || echo unknown)" >> "$LOG"
echo "Date: $(date)" >> "$LOG"
echo "" >> "$LOG"

# --- PRE: prime driver regdom to US (simulates asiair.sh 2.6.4+ boot block) ---
echo "--- PRE: wl country US (simulate asiair.sh 2.6.4+ boot-time regdom prime) ---" >> "$LOG"
sudo systemctl stop hostapd.service
sudo wl country US >> "$LOG" 2>&1
sleep 1
echo "runtime wl country: $(sudo wl country 2>&1)" >> "$LOG"
echo "" >> "$LOG"

# --- Test A: channel=36 (factory default) ---
cp "$AP_CONF" "$TMP_CONF"
sed -i 's/^channel=.*/channel=36/' "$TMP_CONF"
sed -i 's/^autochannel_enabled=.*/autochannel_enabled=0/' "$TMP_CONF"
echo "--- TEST A: channel=36 autochannel_enabled=0 (PRIMED with wl country US) ---" >> "$LOG"
sudo timeout 15 "$NEW" -dd "$TMP_CONF" >> "$LOG" 2>&1 || true
echo "--- TEST A exit ---" >> "$LOG"
echo "" >> "$LOG"

# --- Test B: channel=0 ACS ---
cp "$AP_CONF" "$TMP_CONF"
sed -i 's/^channel=.*/channel=0/' "$TMP_CONF"
if grep -q '^autochannel_enabled=' "$TMP_CONF"; then
    sed -i 's/^autochannel_enabled=.*/autochannel_enabled=1/' "$TMP_CONF"
else
    echo 'autochannel_enabled=1' >> "$TMP_CONF"
fi
echo "--- TEST B: channel=0 autochannel_enabled=1 ---" >> "$LOG"
sudo timeout 8 "$NEW" -dd "$TMP_CONF" >> "$LOG" 2>&1 || true
echo "--- TEST B exit ---" >> "$LOG"

# Restore original hostapd
sudo systemctl start hostapd.service
echo "" >> "$LOG"
echo "=== original hostapd restored ===" >> "$LOG"
REMOTE_SCRIPT
    ssh_run "chmod +x /tmp/run_hostapd_test.sh"
    info "Test script written."

    step "3. Launch test detached (SSH will drop when AP goes down)"
    echo ""
    echo "    SSH connection will drop — that is expected."
    echo "    Waiting up to 45 seconds for AP to restore..."
    echo ""
    ssh_run "nohup /tmp/run_hostapd_test.sh > /tmp/run_hostapd_test.stdout 2>&1 &"

    step "4. Waiting for AP to restore"
    RECONNECTED=0
    for i in $(seq 1 9); do
        sleep 5
        printf "    attempt %d/9... " "$i"
        if ssh $SSH_OPTS ${DEVICE_USER}@${DEVICE_IP} true 2>/dev/null; then
            echo "reconnected."
            RECONNECTED=1
            break
        else
            echo "not yet"
        fi
    done

    if [ "$RECONNECTED" -eq 0 ]; then
        echo ""
        echo "ERROR: Could not reconnect after 45s."
        echo "Try: ssh pi@${DEVICE_IP} 'cat /tmp/hostapd_test_results.log'"
        exit 1
    fi

    step "5. Test results"
    echo ""
    ssh_run "cat /tmp/hostapd_test_results.log 2>/dev/null || echo '(log not found)'"

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Cleanup: ssh pi@${DEVICE_IP} 'rm /tmp/hostapd_new /tmp/hostapd_test_results.log /tmp/run_hostapd_test.sh'"
    exit 0
fi
