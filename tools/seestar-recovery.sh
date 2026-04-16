#!/bin/bash
# Seestar S50 post-flash recovery and pre-upgrade configuration
# Idempotent — safe to run multiple times; each step only acts if needed.
# Backups are written to /home/pi/.ZWO/recovery-backup/ before any file is
# modified; --restore brings every managed file back to its backed-up state.
#
# Usage:
#   ./seestar-recovery.sh               Print current device state (no changes)
#   ./seestar-recovery.sh --apply       Apply configuration (wpa_svr=1, ccode=US)
#   ./seestar-recovery.sh --pre-upgrade Apply config with wpa_svr=0, ccode=US (before 5.84 upgrade)
#   ./seestar-recovery.sh --restore     Restore all managed files from backup
#
# Why ccode=US:
#   fw_2.6.4 asiair.sh line 34 unconditionally runs "sudo wl country $ccode"
#   before hostapd starts, regardless of wpa_svr. With ccode= empty that
#   becomes "wl country" with no argument. What the Broadcom wl tool does
#   with an empty argument is unknown; setting ccode=US passes a valid value.
#
# Why wpa_svr=0 before upgrading to 5.84:
#   fw_2.6.4 asiair.sh lines 39-48 gate both wpa_supplicant startup and
#   "network.sh auto" inside "if wpa_svr=1". network.sh auto (line 341)
#   calls "wpa_cli -i wlan0 reconfigure", which tells wpa_supplicant to
#   rescan. Whether that scan is what breaks the AP is not proven from code.

set -e

DEVICE_IP="10.0.0.1"
DEVICE_USER="pi"
DEFAULT_PASS="raspberry"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o PasswordAuthentication=yes -o PubkeyAuthentication=yes"
LICENSE_SRC="$(dirname "$0")/s50-fs/home/pi/.ZWO/zwoair_license"
LICENSE_MD5="c414956cdbe8bea4e7c6ba89a0a16328"
BACKUP_DIR="/home/pi/.ZWO/recovery-backup"
FW_DIR="$(dirname "$0")/seestar-analysis/output/_fw_work"

# Desired wpa_supplicant.conf — Buffalo Jump Ranch only
DESIRED_WPA='ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
	ssid="Buffalo Jump Ranch"
	psk=7a1818f2bd1f56f55a3655c093e708c42db096601b4982f06d2832f8d343d3d9
}
'

# ── mode parsing ──────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTION]

  (no args)       Print current device state — no changes made
  --apply         Apply configuration: wpa_svr=1, channel=0,
                    wlan0.conf→AP_5G.conf, Buffalo Jump Ranch only
  --pre-upgrade   Same as --apply but sets wpa_svr=0 and channel=36;
                    also registers asiair in dpkg to block auto-downgrade
  --restore       Restore all managed files from backup in $BACKUP_DIR
  --install-key   Copy your SSH public key to the device (one-time setup,
                    uses password auth; after this no password prompts)
  --ip <addr>     Override device IP (default: $DEVICE_IP)
                    e.g. $0 --ip 192.168.1.42 --status
  --help          Show this help

Notes:
  wpa_svr=0: asiair.sh gates both wpa_supplicant startup and
    "network.sh auto" on wpa_svr=1. Setting 0 keeps the AP clean
    before the firmware upgrade.

  dpkg registration: test_asiair_file.sh runs on every boot and checks
    "dpkg -s asiair | grep Version". The dpkg database is empty on this
    device so the check always fails, triggering run_old_update.sh
    --autodowngrade which installs the embedded 2.71 imager over 6.45.
    Registering a stub entry prevents the auto-downgrade.
EOF
}

MODE="status"
WPA_SVR=1

# Pre-scan for --ip so it works in any position
args=("$@")
filtered=()
i=0
while [ $i -lt ${#args[@]} ]; do
    if [ "${args[$i]}" = "--ip" ]; then
        i=$((i+1))
        DEVICE_IP="${args[$i]:?--ip requires an address}"
    else
        filtered+=("${args[$i]}")
    fi
    i=$((i+1))
done
set -- "${filtered[@]+"${filtered[@]}"}"

case "${1:-}" in
    --apply)        MODE="apply" ;;
    --restore)      MODE="restore" ;;
    --pre-upgrade)  MODE="apply"; WPA_SVR=0 ;;
    --install-key)  MODE="install-key" ;;
    --help|-h)      usage; exit 0 ;;
    "")             MODE="status" ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
esac

# ── helpers ───────────────────────────────────────────────────────────────────
ssh_run() { ssh $SSH_OPTS ${DEVICE_USER}@${DEVICE_IP} "$@"; }
scp_to()  { scp $SSH_OPTS "$1" ${DEVICE_USER}@${DEVICE_IP}:"$2"; }

step()    { echo ""; echo "==> $*"; }
ok()      { echo "    [OK] already correct — no change"; }
changed() { echo "    [CHANGED] $*"; }
info()    { echo "    $*"; }

show_value() {
    local label="$1" val="$2"
    printf "  %-38s %s\n" "$label" "$val"
}

# Back up a file on the device (only if backup doesn't already exist)
backup_file() {
    local src="$1"
    local name
    name=$(basename "$src")
    ssh_run "
        sudo mkdir -p '$BACKUP_DIR'
        if [ ! -f '$BACKUP_DIR/$name' ]; then
            if [ -f '$src' ]; then
                sudo cp -p '$src' '$BACKUP_DIR/$name'
                echo '    [BACKUP] saved $src'
            fi
        fi
    "
}

# ── SSH key install mode ──────────────────────────────────────────────────────
if [ "$MODE" = "install-key" ]; then
    echo ""
    echo "Seestar S50 Recovery Tool  [mode: install-key]"
    echo "Installing SSH public key on device (password will be required once)."
    echo ""
    # Find the default public key
    PUBKEY=""
    for candidate in ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub ~/.ssh/id_ecdsa.pub; do
        if [ -f "$candidate" ]; then
            PUBKEY="$candidate"
            break
        fi
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
    exit 0
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
# CURRENT STATE — always printed regardless of mode
# ═════════════════════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════ CURRENT STATE ════════════════════════"

# Firmware version
FW_VER=$(ssh_run "grep '^version_string=' /home/pi/ASIAIR/config 2>/dev/null | cut -d= -f2" || true)
FW_INT=$(ssh_run "grep '^version_int=' /home/pi/ASIAIR/config 2>/dev/null | cut -d= -f2" || true)
show_value "firmware version:" "${FW_VER:-'(unknown)'}  (version_int=${FW_INT:-'?'})"

# License
DEVICE_MD5=$(ssh_run "md5sum /home/pi/.ZWO/zwoair_license 2>/dev/null | awk '{print \$1}'" || true)
if [ -z "$DEVICE_MD5" ]; then
    show_value "license md5:" "(not present)"
elif [ "$DEVICE_MD5" = "$LICENSE_MD5" ]; then
    show_value "license md5:" "$DEVICE_MD5  [GOOD]"
else
    show_value "license md5:" "$DEVICE_MD5  [WRONG — expected $LICENSE_MD5]"
fi

# ap_id_inited — imager runs as pi (rc.local: sudo -u pi), HOME=/home/pi
PI_APID=$(ssh_run 'grep -c "ap_id_inited.*true" /home/pi/.ZWO/ASIAIR_general.xml 2>/dev/null || echo 0')
[ "$PI_APID" = "1" ] && PI_APID_STR="OK" || PI_APID_STR="MISSING/WRONG"
show_value "ap_id_inited /home/pi/.ZWO:" "$PI_APID_STR"

# dpkg — shows what test_asiair_file.sh sees when it checks package registration
DPKG_ASIAIR=$(ssh_run 'dpkg -s asiair 2>/dev/null | grep "^Version:" || echo "(not registered)"')
show_value "dpkg asiair:" "$DPKG_ASIAIR"

# sh_conf.txt
CURRENT_CONF=$(ssh_run 'cat /home/pi/.ZWO/sh_conf.txt 2>/dev/null || true')
WPA_SVR_NOW=$(echo "$CURRENT_CONF" | grep '^wpa_svr=' | head -1 || true)
CCODE_NOW=$(echo "$CURRENT_CONF"   | grep '^ccode='   | head -1 || true)
show_value "sh_conf.txt  wpa_svr:" "${WPA_SVR_NOW:-'(missing)'}"
show_value "sh_conf.txt  ccode:"   "${CCODE_NOW:-'(missing)'}"

# AP_5G.conf
AP_CHANNEL_NOW=$(ssh_run "grep '^channel='            /home/pi/AP_5G.conf 2>/dev/null || true")
AP_AUTO_NOW=$(   ssh_run "grep '^autochannel_enabled=' /home/pi/AP_5G.conf 2>/dev/null || true")
show_value "AP_5G.conf  channel:"            "${AP_CHANNEL_NOW:-'(missing)'}"
show_value "AP_5G.conf  autochannel_enabled:" "${AP_AUTO_NOW:-'(missing)'}"

# wlan0.conf symlink
LINK_TARGET=$(ssh_run "readlink /home/pi/wlan0.conf 2>/dev/null || true")
show_value "wlan0.conf symlink:" "${LINK_TARGET:-'(not a symlink / not present)'}"

# wpa_supplicant.conf — show SSIDs only (don't echo PSKs to terminal)
SSIDS=$(ssh_run "grep '^\s*ssid=' /home/pi/wpa_supplicant.conf 2>/dev/null | sed 's/.*ssid=//' | tr '\n' ' '" || true)
COUNTRY_NOW=$(ssh_run "grep '^country=' /home/pi/wpa_supplicant.conf 2>/dev/null || true")
show_value "wpa_supplicant  country:" "${COUNTRY_NOW:-'(missing)'}"
show_value "wpa_supplicant  networks:" "${SSIDS:-'(none)'}"

# Stale configs
STALE=$(ssh_run 'find /home/pi/.ZWO -maxdepth 1 \( \( -name "*.xml" ! -name "ASIAIR_general.xml" \) -o -name "*.json" \) -o \( -name "*.txt" ! -name "sh_conf.txt" \) 2>/dev/null | sort || true')
if [ -n "$STALE" ]; then
    show_value "stale configs in .ZWO:" "$(echo "$STALE" | tr '\n' ' ')"
else
    show_value "stale configs in .ZWO:" "(none)"
fi

# Backup dir
BACKUP_EXISTS=$(ssh_run "ls '$BACKUP_DIR' 2>/dev/null | head -5 || echo '(none)'")
show_value "backup dir $BACKUP_DIR:" "$BACKUP_EXISTS"

echo "════════════════════════════════════════════════════════════════"

# ── status-only mode exits here ───────────────────────────────────────────────
if [ "$MODE" = "status" ]; then
    echo ""
    echo "Status only — no changes made."
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# RESTORE MODE
# ═════════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "restore" ]; then
    echo ""
    echo "════════════════════════ RESTORE ═══════════════════════════════"
    BACKUP_FILES=$(ssh_run "ls '$BACKUP_DIR' 2>/dev/null || true")
    if [ -z "$BACKUP_FILES" ]; then
        echo "ERROR: No backups found in $BACKUP_DIR"
        exit 1
    fi
    echo "  Restoring from $BACKUP_DIR:"
    ssh_run "
        set -e
        for f in '$BACKUP_DIR'/*; do
            name=\$(basename \"\$f\")
            case \"\$name\" in
                sh_conf.txt)       dst='/home/pi/.ZWO/sh_conf.txt' ;;
                AP_5G.conf)        dst='/home/pi/AP_5G.conf' ;;
                wpa_supplicant.conf) dst='/home/pi/wpa_supplicant.conf' ;;
                *)                 echo \"  [SKIP] unknown backup file: \$name\"; continue ;;
            esac
            cp -p \"\$f\" \"\$dst\"
            echo \"  [RESTORED] \$name -> \$dst\"
        done
    "
    # wlan0.conf symlink cannot be easily backed up; just report its state
    echo ""
    echo "  Note: wlan0.conf symlink was not changed by restore."
    echo "        Current target: ${LINK_TARGET:-'(not present)'}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Restore complete. Reboot the device for changes to take effect."
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# APPLY MODE
# ═════════════════════════════════════════════════════════════════════════════
if [ "$WPA_SVR" = "0" ]; then
    echo ""
    echo "*** PRE-UPGRADE MODE: wpa_svr will be set to 0 ***"
fi

echo ""
echo "════════════════════════ APPLYING CHANGES ══════════════════════"

# ── 1. License file ───────────────────────────────────────────────────────────
step "1. License file"
if [ ! -f "$LICENSE_SRC" ]; then
    echo "ERROR: License source not found: $LICENSE_SRC"; exit 1
fi
LOCAL_MD5=$(md5sum "$LICENSE_SRC" | awk '{print $1}')
if [ "$LOCAL_MD5" != "$LICENSE_MD5" ]; then
    echo "ERROR: Local license md5 mismatch (got $LOCAL_MD5, expected $LICENSE_MD5)"; exit 1
fi

if [ "$DEVICE_MD5" = "$LICENSE_MD5" ]; then
    ok
else
    info "Copying license file (device had: ${DEVICE_MD5:-missing})..."
    ssh_run "mkdir -p /home/pi/.ZWO"
    scp $SSH_OPTS "$LICENSE_SRC" ${DEVICE_USER}@${DEVICE_IP}:/home/pi/.ZWO/zwoair_license
    changed "license installed"
fi

# ── 2. Stale config files ─────────────────────────────────────────────────────
step "2. Stale config files (*.xml *.json *.txt except sh_conf.txt and ASIAIR_general.xml)"
# CRITICAL: ASIAIR_general.xml must be preserved (or rewritten) with ap_id_inited=true.
# The 6.45 imager checks setting2/network/ap_id_inited at startup. If missing, it runs
# AP initialization which calls network.sh run_5g 1 → restart_ap() → hostapd stop/start.
# During that restart window (especially with ACS/channel=0), the WiFi monitor finds the
# AP null and plays sound 33 ("WiFi is abnormal").
if [ -z "$STALE" ]; then
    ok
else
    info "Removing: $STALE"
    ssh_run '
        cd /home/pi/.ZWO
        for f in *.xml *.json; do
            [ "$f" = "ASIAIR_general.xml" ] && continue
            [ -e "$f" ] && rm -v "$f"
        done
        for f in *.txt; do [ "$f" = "sh_conf.txt" ] || { [ -e "$f" ] && rm -v "$f"; }; done
    '
    changed "stale files removed (ASIAIR_general.xml preserved)"
fi

step "2b. ASIAIR_general.xml  (ap_id_inited=true) — /home/pi/.ZWO/"
# Imager runs as pi (rc.local: sudo -u pi /home/pi/ASIAIR/asiair.sh), HOME=/home/pi.
PI_OK=$(ssh_run 'grep -c "ap_id_inited.*true" /home/pi/.ZWO/ASIAIR_general.xml 2>/dev/null || echo 0')

if [ "$PI_OK" = "1" ]; then
    ok
else
    ssh_run 'cat > /home/pi/.ZWO/ASIAIR_general.xml << '"'"'EOF'"'"'
<?xml version="1.0" encoding="UTF-8" ?>
<setting2 date="20190214_181215">
    <network date="20190214_181215">
        <ap_id_inited type="8" date="20190214_181215">true</ap_id_inited>
    </network>
</setting2>
EOF'
    changed "wrote /home/pi/.ZWO/ASIAIR_general.xml with ap_id_inited=true"
fi

# ── 3. sh_conf.txt ────────────────────────────────────────────────────────────
step "3. /home/pi/.ZWO/sh_conf.txt  (wpa_svr=${WPA_SVR}, ccode=US)"
# ccode=US is required: 5.84's asiair.sh runs "sudo wl country $ccode" unconditionally
# before hostapd starts. Empty ccode leaves the WiFi driver in a bad state, hostapd
# fails to bring up uap0, AP never comes back, sound 33 plays.
DESIRED_CONF="wpa_svr=${WPA_SVR}
ccode=US"
if [ "$CURRENT_CONF" = "$DESIRED_CONF" ]; then
    ok
else
    backup_file "/home/pi/.ZWO/sh_conf.txt"
    info "Was: $(echo "$CURRENT_CONF" | tr '\n' '|')"
    ssh_run "sudo sh -c \"printf 'wpa_svr=${WPA_SVR}\nccode=US\n' > /home/pi/.ZWO/sh_conf.txt\""
    changed "wpa_svr=${WPA_SVR} ccode=US"
fi

# ── 4. AP_5G.conf — channel and ACS ─────────────────────────────────────────
# --pre-upgrade: keep channel=36 (fast AP startup, no ACS delay at boot).
#   ACS is NOT needed before the upgrade. channel=0 causes hostapd to do a
#   5-30 second ACS scan on every restart; the imager checks AP state during
#   that window, gets null, and plays sound 33. The app's "network.sh country
#   US" call (Phase 7 WiFi setup) already sets channel=0/autochannel_enabled=1
#   correctly — we do not need to pre-configure it.
# --apply (wpa_svr=1): set channel=0, autochannel_enabled=1 for SCC support.
if [ "$WPA_SVR" = "1" ]; then
    step "4. /home/pi/AP_5G.conf  (channel=0, autochannel_enabled=1 — SCC mode)"
    if [ "$AP_CHANNEL_NOW" = "channel=0" ] && [ "$AP_AUTO_NOW" = "autochannel_enabled=1" ]; then
        ok
    else
        backup_file "/home/pi/AP_5G.conf"
        info "Was: $AP_CHANNEL_NOW  $AP_AUTO_NOW"
        ssh_run '
            sudo sed -i "s/^channel=.*/channel=0/" /home/pi/AP_5G.conf
            if grep -q "^autochannel_enabled=" /home/pi/AP_5G.conf; then
                sudo sed -i "s/^autochannel_enabled=.*/autochannel_enabled=1/" /home/pi/AP_5G.conf
            else
                sudo sh -c "echo autochannel_enabled=1 >> /home/pi/AP_5G.conf"
            fi
        '
        changed "channel=0, autochannel_enabled=1"
    fi
else
    step "4. /home/pi/AP_5G.conf  (channel=36 — fast startup, no ACS delay)"
    if [ "$AP_CHANNEL_NOW" = "channel=36" ]; then
        ok
    else
        backup_file "/home/pi/AP_5G.conf"
        info "Was: $AP_CHANNEL_NOW  $AP_AUTO_NOW"
        ssh_run '
            sudo sed -i "s/^channel=.*/channel=36/" /home/pi/AP_5G.conf
            if grep -q "^autochannel_enabled=" /home/pi/AP_5G.conf; then
                sudo sed -i "s/^autochannel_enabled=.*/autochannel_enabled=0/" /home/pi/AP_5G.conf
            fi
        '
        changed "channel=36, autochannel_enabled=0 (app will enable ACS via network.sh country US)"
    fi
fi

# ── 5. wlan0.conf symlink → AP_5G.conf ───────────────────────────────────────
step "5. /home/pi/wlan0.conf  (symlink → AP_5G.conf)"
if [ "$LINK_TARGET" = "AP_5G.conf" ] || [ "$LINK_TARGET" = "/home/pi/AP_5G.conf" ]; then
    ok
else
    info "Was: ${LINK_TARGET:-'(not present)'}"
    ssh_run "sudo ln -sf /home/pi/AP_5G.conf /home/pi/wlan0.conf"
    changed "wlan0.conf -> AP_5G.conf"
fi

# ── 6. wpa_supplicant.conf (--apply / station mode only) ─────────────────────
# Skipped in --pre-upgrade: wpa_svr=0 means wpa_supplicant never starts, so
# network config doesn't matter until the app configures WiFi (Phase 7).
if [ "$WPA_SVR" = "1" ]; then
    step "6. /home/pi/wpa_supplicant.conf  (Buffalo Jump Ranch only, country=US)"
    CURRENT_WPA=$(ssh_run 'cat /home/pi/wpa_supplicant.conf 2>/dev/null || true')
    if [ "$CURRENT_WPA" = "$DESIRED_WPA" ]; then
        ok
    else
        backup_file "/home/pi/wpa_supplicant.conf"
        info "Was networks: $SSIDS  country: $COUNTRY_NOW"
        ssh_run "sudo sh -c 'cat > /home/pi/wpa_supplicant.conf'" <<'EOF'
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
	ssid="Buffalo Jump Ranch"
	psk=7a1818f2bd1f56f55a3655c093e708c42db096601b4982f06d2832f8d343d3d9
}
EOF
        changed "Buffalo Jump Ranch only, country=US"
    fi
else
    step "6. wpa_supplicant.conf  (skipped — wpa_svr=0, not needed pre-upgrade)"
    ok
fi


# ── Post-apply state summary ──────────────────────────────────────────────────
echo ""
echo "════════════════════════ POST-APPLY STATE ══════════════════════"
ssh_run '
    printf "  %-38s %s\n" "firmware:" "$(grep "^version_string=" /home/pi/ASIAIR/config 2>/dev/null | cut -d= -f2 || echo MISSING)"
    printf "  %-38s %s\n" "license md5:"  "$(md5sum /home/pi/.ZWO/zwoair_license 2>/dev/null | awk "{print \$1}" || echo MISSING)"
    printf "  %-38s %s\n" "ap_id_inited /home/pi:" "$(grep -q "ap_id_inited.*true" /home/pi/.ZWO/ASIAIR_general.xml 2>/dev/null && echo OK || echo MISSING/WRONG)"
    printf "  %-38s %s\n" "sh_conf.txt:"  "$(cat /home/pi/.ZWO/sh_conf.txt 2>/dev/null | tr "\n" "|" || echo MISSING)"
    printf "  %-38s %s\n" "AP_5G channel:" "$(grep "^channel=" /home/pi/AP_5G.conf 2>/dev/null || echo MISSING)"
    printf "  %-38s %s\n" "AP_5G autochannel:" "$(grep "^autochannel_enabled=" /home/pi/AP_5G.conf 2>/dev/null || echo MISSING)"
    printf "  %-38s %s\n" "wlan0.conf symlink:" "$(readlink /home/pi/wlan0.conf 2>/dev/null || echo MISSING)"
    printf "  %-38s %s\n" "wpa networks:" "$(grep "ssid=" /home/pi/wpa_supplicant.conf 2>/dev/null | sed "s/.*ssid=//" | tr "\n" " " || echo MISSING)"
    printf "  %-38s %s\n" "wpa country:" "$(grep "^country=" /home/pi/wpa_supplicant.conf 2>/dev/null || echo MISSING)"
'
echo "════════════════════════════════════════════════════════════════"
echo ""
if [ "$WPA_SVR" = "1" ]; then
    echo "Device ready.  wpa_svr=1, ccode=US — station mode active at boot."
    echo ""
    echo "BEFORE upgrading to firmware 5.84, run:"
    echo "  $0 --pre-upgrade"
    echo "After upgrading, configure home WiFi through the Seestar app,"
    echo "then run '$0 --apply' to restore station mode."
else
    echo "Device ready for firmware upgrade.  wpa_svr=0, ccode=US, channel=36."
    echo "  - AP starts on channel=36 (no ACS delay — avoids 'WiFi is abnormal' at boot)"
    echo "  - wpa_supplicant will NOT start at boot (asiair.sh lines 39-48)"
    echo "  - network.sh auto will NOT run at boot (same if-block)"
    echo "  - 'wl country US' will run at boot instead of 'wl country' (asiair.sh line 34)"
    echo ""
    echo "After upgrading, configure home WiFi through the Seestar app."
    echo "The app calls network.sh country US which enables ACS (channel=0) properly."
fi
echo ""
echo "To undo all changes:  $0 --restore"
echo "To see current state: $0"
