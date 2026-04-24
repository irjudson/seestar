#!/bin/bash
# Compare 2.42 base image (seestarOS.img) vs s50-fs filesystem snapshot.
# Identifies persistent differences that survive all firmware updates.
#
# Must run as root (sudo) — needs access to /media/irjudson/rootfs and /media/irjudson/pi.
#
# Usage:
#   sudo bash tools/compare_base_to_s50fs.sh

BASE_ROOT="/media/irjudson/rootfs"   # p6 rootfs partition
BASE_HOME="/media/irjudson/pi"       # p5 /home/pi partition
S50FS="/home/irjudson/Projects/Seestar/s50-fs"

if [ -t 1 ]; then
    R="\033[31m" G="\033[32m" Y="\033[33m" B="\033[34m" C="\033[36m" W="\033[0m"
else
    R="" G="" Y="" B="" C="" W=""
fi

hdr()  { printf "\n${B}══════════════════════════════════════════════════════════${W}\n"
         printf "${B}  %s${W}\n" "$1"
         printf "${B}══════════════════════════════════════════════════════════${W}\n\n"; }
ok()   { printf "  ${G}✓${W} %s\n" "$1"; }
warn() { printf "  ${Y}!${W} %s\n" "$1"; }
info() { printf "    %s\n" "$1"; }
drow() { printf "  %-56s  %-16s  %-16s\n" "$1" "$2" "$3"; }
dhdr() { drow "FILE" "BASE-2.42" "S50FS"; }

bmd5() { [ -f "$1" ] && md5sum "$1" | awk '{print $1}' || echo "(absent)"; }

# Files that firmware update scripts replace on S50 — skip these in module/binary scans
UPDATED_FILES="bcmdhd.ko|eaf.ko|video_rkcif.ko|imx462.ko|imx585.ko|pwrled_gpio.ko|
               sshd|sftp-server|sshd-auth|sshd-session|hostapd|wpa_supplicant|
               nginx.conf|dnsmasq.conf|dhcpcd.conf|zwo_deleteStarsTool|
               imx462_CMK|libv4l1|libv4l2|libv4lconvert|libv4l-mplane|v4l1compat|v4l2convert"
UPDATED_RE=$(echo "$UPDATED_FILES" | tr -d ' \n' | sed 's/|/|/g')

is_updated() { echo "$1" | grep -qE "$UPDATED_RE"; }

# ── Preflight ───────────────────────────────────────────────────────
if [ ! -f "$BASE_ROOT/etc/rc.local" ]; then
    printf "${R}ERROR:${W} $BASE_ROOT not accessible. Run:\n"
    printf "  sudo mount -o loop,ro,offset=%s \\\n" "$((1277952*512))"
    printf "    /home/irjudson/Projects/Seestar/baseline-2.42/seestarOS.img /mnt/base\n"
    exit 1
fi
HAVE_HOME=0
[ -d "$BASE_HOME/ASIAIR" ] && HAVE_HOME=1

# ══════════════════════════════════════════════════════════════════
hdr "1. KERNEL & BOOT"
# ══════════════════════════════════════════════════════════════════

printf "  %-20s  %-34s  %-34s\n" "FILE" "BASE-2.42 md5" "S50FS md5"
for f in config.txt Image zImage vmlinuz; do
    b="$BASE_ROOT/boot/$f"
    s="$S50FS/boot/$f"
    [ -f "$b" ] || [ -f "$s" ] || continue
    bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
    if [ "$bm" = "$sm" ]; then
        printf "  %-20s  ${G}identical${W}  (%s)\n" "$f" "$bm"
    else
        printf "  ${Y}%-20s${W}  %s  %s\n" "$f" "$bm" "$sm"
    fi
done

printf "\n  DTB files (those that differ):\n"
dhdr
found_dtb=0
while IFS= read -r bdtb; do
    rel="${bdtb#$BASE_ROOT}"
    sdtb="$S50FS$rel"
    bm=$(bmd5 "$bdtb")
    sm=$(bmd5 "$sdtb")
    [ "$bm" = "$sm" ] && continue
    drow "$rel" "${bm:0:14}" "${sm:0:14}"
    found_dtb=1
done < <(find "$BASE_ROOT/boot" -name "*.dtb" 2>/dev/null | sort)
while IFS= read -r sdtb; do
    rel="${sdtb#$S50FS}"
    [ -f "$BASE_ROOT$rel" ] && continue
    drow "$rel" "(absent)" "$(bmd5 "$sdtb" | cut -c1-14)"
    found_dtb=1
done < <(find "$S50FS/boot" -name "*.dtb" 2>/dev/null | sort)
[ "$found_dtb" -eq 0 ] && ok "All DTBs identical (or none present)"

# ══════════════════════════════════════════════════════════════════
hdr "2. rc.local  (NEVER updated for S50 — persists from base image)"
# ══════════════════════════════════════════════════════════════════

bm=$(bmd5 "$BASE_ROOT/etc/rc.local")
sm=$(bmd5 "$S50FS/etc/rc.local")
if [ "$bm" = "$sm" ]; then
    ok "rc.local identical ($bm)"
else
    warn "rc.local DIFFERS — base-2.42 vs s50-fs:"
    diff --unified=3 --label "base-2.42" --label "s50-fs" \
        "$BASE_ROOT/etc/rc.local" "$S50FS/etc/rc.local" || true
fi

# ══════════════════════════════════════════════════════════════════
hdr "3. WIFI FIRMWARE BLOBS  (never updated by any fw package)"
# ══════════════════════════════════════════════════════════════════

for blob in fw_bcm43752a2_ag.bin fw_bcm43752a2_ag_apsta.bin fw_bcm43752a2_ag_mfg.bin \
            fw_bcm43456c5_ag.bin fw_bcm43456c5_ag_apsta.bin \
            fw_bcm43438a1.bin nvram_ap6256.txt nvram_ap6275s.txt nvram_ap6212a.txt; do
    b="$BASE_ROOT/usr/lib/firmware/$blob"
    s="$S50FS/usr/lib/firmware/$blob"
    [ -f "$b" ] || [ -f "$s" ] || continue
    bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
    if [ "$bm" = "$sm" ]; then ok "$blob: identical"
    else warn "$blob: DIFFERS"; info "  base: $bm"; info "  s50:  $sm"; fi
done

# ══════════════════════════════════════════════════════════════════
hdr "4. KERNEL MODULES  (only specific .ko files are updated per-fw)"
# ══════════════════════════════════════════════════════════════════

printf "  Modules that differ (excluding known-updated ones):\n"
dhdr
found_ko=0
while IFS= read -r bko; do
    rel="${bko#$BASE_ROOT}"
    is_updated "$rel" && continue
    sko="$S50FS$rel"
    bm=$(bmd5 "$bko"); sm=$(bmd5 "$sko")
    [ "$bm" = "$sm" ] && continue
    drow "$rel" "${bm:0:14}" "${sm:0:14}"
    found_ko=1
done < <(find "$BASE_ROOT/lib/modules" -name "*.ko" 2>/dev/null | sort)
# Modules only in one side
while IFS= read -r sko; do
    rel="${sko#$S50FS}"
    is_updated "$rel" && continue
    [ -f "$BASE_ROOT$rel" ] && continue
    drow "$rel" "(absent)" "only-in-s50"
    found_ko=1
done < <(find "$S50FS/lib/modules" -name "*.ko" 2>/dev/null | grep -v "/proc/" | sort)
[ "$found_ko" -eq 0 ] && ok "All non-updated modules identical"

# ══════════════════════════════════════════════════════════════════
hdr "5. MODPROBE CONFIG  (never updated)"
# ══════════════════════════════════════════════════════════════════

found_mod=0
while IFS= read -r f; do
    rel="${f#$BASE_ROOT}"
    sf="$S50FS$rel"
    bm=$(bmd5 "$f"); sm=$(bmd5 "$sf")
    if [ "$bm" = "$sm" ]; then ok "$rel"
    else
        warn "$rel DIFFERS:"
        diff --unified=2 --label "base-2.42" --label "s50-fs" "$f" "$sf" 2>/dev/null || true
        found_mod=1
    fi
done < <(find "$BASE_ROOT/etc/modprobe.d" -type f 2>/dev/null | sort)
while IFS= read -r f; do
    rel="${f#$S50FS}"
    [ -f "$BASE_ROOT$rel" ] || { warn "$rel: only in s50-fs"; found_mod=1; }
done < <(find "$S50FS/etc/modprobe.d" -type f 2>/dev/null | sort)
[ "$found_mod" -eq 0 ] && ok "All modprobe.d configs identical"

# ══════════════════════════════════════════════════════════════════
hdr "6. INIT SCRIPTS & SYSTEMD UNITS  (not all are updated)"
# ══════════════════════════════════════════════════════════════════

printf "  /etc/init.d scripts that differ (excluding updated ones):\n"
dhdr
found_init=0
while IFS= read -r b; do
    rel="${b#$BASE_ROOT}"
    is_updated "$rel" && continue
    s="$S50FS$rel"
    bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
    [ "$bm" = "$sm" ] && continue
    drow "$rel" "${bm:0:14}" "${sm:0:14}"
    found_init=1
done < <(find "$BASE_ROOT/etc/init.d" -type f 2>/dev/null | sort)
[ "$found_init" -eq 0 ] && ok "All non-updated init.d scripts identical"

printf "\n  systemd units that differ:\n"
dhdr
found_svc=0
while IFS= read -r b; do
    rel="${b#$BASE_ROOT}"
    s="$S50FS$rel"
    bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
    [ "$bm" = "$sm" ] && continue
    drow "$rel" "${bm:0:14}" "${sm:0:14}"
    found_svc=1
done < <(find "$BASE_ROOT/lib/systemd" "$BASE_ROOT/etc/systemd" \
    -name "*.service" -o -name "*.timer" -o -name "*.socket" -o -name "*.mount" \
    2>/dev/null | sort)
[ "$found_svc" -eq 0 ] && ok "All systemd units identical"

# ══════════════════════════════════════════════════════════════════
hdr "7. NETWORK & IDENTITY CONFIG"
# ══════════════════════════════════════════════════════════════════

for f in /etc/hostname /etc/hosts /etc/fstab \
          /etc/network/interfaces /etc/dhcpcd.conf \
          /etc/wpa_supplicant/wpa_supplicant.conf \
          /etc/default/hostapd /etc/hostapd/hostapd.conf; do
    b="$BASE_ROOT$f"; s="$S50FS$f"
    [ -f "$b" ] || [ -f "$s" ] || continue
    bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
    if [ "$bm" = "$sm" ]; then ok "$f: identical"
    else
        warn "$f: DIFFERS"
        diff --unified=3 --label "base-2.42" --label "s50-fs" "$b" "$s" 2>/dev/null || true
    fi
done

# ══════════════════════════════════════════════════════════════════
hdr "8. KEY SYSTEM BINARIES  (not in the update list)"
# ══════════════════════════════════════════════════════════════════

printf "  Binaries that differ (excluding known-updated ones):\n"
dhdr
found_bin=0
for dir in /sbin /usr/sbin /bin /usr/bin; do
    while IFS= read -r b; do
        rel="${b#$BASE_ROOT}"
        is_updated "$rel" && continue
        s="$S50FS$rel"
        bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
        [ "$bm" = "$sm" ] && continue
        drow "$rel" "${bm:0:14}" "${sm:0:14}"
        found_bin=1
    done < <(find "$BASE_ROOT$dir" -maxdepth 1 -type f 2>/dev/null | sort)
done
[ "$found_bin" -eq 0 ] && ok "All non-updated binaries identical"

# ══════════════════════════════════════════════════════════════════
hdr "9. /etc/zwo  (ZWO-specific config)"
# ══════════════════════════════════════════════════════════════════

found_zwo=0
while IFS= read -r b; do
    rel="${b#$BASE_ROOT}"
    is_updated "$rel" && continue
    s="$S50FS$rel"
    bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
    if [ "$bm" = "$sm" ]; then ok "$rel"
    else
        warn "$rel: DIFFERS"; drow "$rel" "${bm:0:14}" "${sm:0:14}"
        found_zwo=1
        # Show text file diffs
        file "$b" 2>/dev/null | grep -q "text" && \
            diff --unified=3 --label "base-2.42" --label "s50-fs" "$b" "$s" 2>/dev/null || true
    fi
done < <(find "$BASE_ROOT/etc/zwo" -type f 2>/dev/null | sort)
while IFS= read -r s; do
    rel="${s#$S50FS}"
    [ -f "$BASE_ROOT$rel" ] || { warn "$rel: only in s50-fs"; found_zwo=1; }
done < <(find "$S50FS/etc/zwo" -type f 2>/dev/null | sort)
[ "$found_zwo" -eq 0 ] && ok "All /etc/zwo files identical"

# ══════════════════════════════════════════════════════════════════
hdr "10. /home/pi  (app version, identity, config — p5 partition)"
# ══════════════════════════════════════════════════════════════════

if [ "$HAVE_HOME" -eq 0 ]; then
    warn "pi partition ($BASE_HOME) not available or empty — skipping"
else
    # App version
    b_ver=$(cat "$BASE_HOME/ASIAIR/version.txt" 2>/dev/null || echo "(no version.txt)")
    s_ver=$(cat "$S50FS/home/pi/ASIAIR/version.txt" 2>/dev/null || echo "(no version.txt)")
    info "ASIAIR app version in base-2.42: $b_ver"
    info "ASIAIR app version in s50-fs:    $s_ver"
    echo ""

    # Donor unit identity
    for xml in ASIAIR_general.xml ASIAIR_General.xml; do
        b="$BASE_HOME/.ZWO/$xml"
        [ -f "$b" ] || continue
        warn "$xml (donor unit identity baked into base image):"
        grep -iE "ap_id|serial|device_id|mac|unit_id|apid" "$b" 2>/dev/null | sed 's/^/    /' || true
        echo ""
    done

    # Config files at top level and .ZWO
    printf "  Config/data files that differ:\n"
    dhdr
    found_home=0
    while IFS= read -r b; do
        rel="${b#$BASE_HOME}"
        s="$S50FS/home/pi$rel"
        bm=$(bmd5 "$b"); sm=$(bmd5 "$s")
        [ "$bm" = "$sm" ] && continue
        drow "/home/pi$rel" "${bm:0:14}" "${sm:0:14}"
        found_home=1
    done < <(find "$BASE_HOME" -maxdepth 3 -type f \
        \( -name "*.conf" -o -name "*.txt" -o -name "*.xml" -o -name "*.json" -o -name "*.sh" \) \
        2>/dev/null | sort)
    [ "$found_home" -eq 0 ] && ok "All comparable home files identical"
fi

# ══════════════════════════════════════════════════════════════════
hdr "11. FILES PRESENT IN ONE SIDE ONLY  (key dirs, depth 3)"
# ══════════════════════════════════════════════════════════════════

printf "  Only in base-2.42 (not in s50-fs):\n"
found_only=0
for dir in /etc /lib/modules /usr/lib/firmware /usr/bin /usr/sbin /sbin /bin; do
    while IFS= read -r b; do
        rel="${b#$BASE_ROOT}"
        [ -e "$S50FS$rel" ] && continue
        printf "    BASE-ONLY: %s\n" "$rel"
        found_only=1
    done < <(find "$BASE_ROOT$dir" -maxdepth 3 -type f 2>/dev/null | sort)
done
[ "$found_only" -eq 0 ] && ok "No base-only files found in scanned dirs"

echo ""
printf "  Only in s50-fs (not in base-2.42):\n"
found_only=0
for dir in /etc /lib/modules /usr/lib/firmware /usr/bin /usr/sbin /sbin /bin; do
    while IFS= read -r s; do
        rel="${s#$S50FS}"
        echo "$rel" | grep -q "/proc/" && continue
        [ -e "$BASE_ROOT$rel" ] && continue
        printf "    S50-ONLY:  %s\n" "$rel"
        found_only=1
    done < <(find "$S50FS$dir" -maxdepth 3 -type f 2>/dev/null | sort)
done
[ "$found_only" -eq 0 ] && ok "No s50-only files found in scanned dirs"

printf "\n${G}══ Done ══${W}\n"
