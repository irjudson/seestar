#!/bin/bash
# Audit bcmdhd.ko across every firmware package in the repo. Print md5 +
# compile-date string + module version string for each. Highlights:
#   - factory (Jul 2023)  ← works on our chip
#   - fw_2.2.0 onwards (Oct 2025)  ← regression
#   - any later rebuild?  ← potential fix without needing to stay on 5.50
#
# Usage: ./tools/audit_bcmdhd_across_versions.sh

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

printf "%-12s %-34s %-32s %-22s %s\n" \
    "SOURCE" "MD5" "COMPILE DATE" "DHD VERSION" "FILE"

# Factory (extracted from baseline-2.42)
factory="$REPO_ROOT/firmware/factory/bcmdhd.ko.jul2023"
if [ -f "$factory" ]; then
    md5=$(md5sum "$factory" | awk '{print $1}')
    cd=$(strings "$factory" | grep "compiled on" | head -1 | sed 's/.*compiled on //')
    ver=$(strings "$factory" | grep -oE "version 101\.[0-9.]+ \(wlan=[^)]+\)" | head -1)
    printf "%-12s %-34s %-32s %-22s %s\n" "FACTORY" "$md5" "$cd" "$ver" "$factory"
else
    printf "%-12s %s\n" "FACTORY" "(not extracted; run extract_factory_bcmdhd.sh)"
fi

# All firmware packages
for pkg in "$REPO_ROOT"/firmware/packages/fw_*/others/bcmdhd.ko; do
    [ -f "$pkg" ] || continue
    ver_dir=$(basename "$(dirname "$(dirname "$pkg")")" | sed 's/^fw_//')
    md5=$(md5sum "$pkg" | awk '{print $1}')
    cd=$(strings "$pkg" | grep "compiled on" | head -1 | sed 's/.*compiled on //')
    dhd_ver=$(strings "$pkg" | grep -oE "version 101\.[0-9.]+ \(wlan=[^)]+\)" | head -1)
    printf "%-12s %-34s %-32s %-22s %s\n" "$ver_dir" "$md5" "$cd" "$dhd_ver" "$pkg"
done

echo ""
echo "Summary: unique drivers across all sources ↓"
{
    [ -f "$factory" ] && md5sum "$factory"
    md5sum "$REPO_ROOT"/firmware/packages/fw_*/others/bcmdhd.ko 2>/dev/null
} | awk '{print $1}' | sort -u | while read m; do
    # Show which sources have this md5
    sources=""
    [ -f "$factory" ] && [ "$(md5sum "$factory" | awk '{print $1}')" = "$m" ] && sources="FACTORY"
    for pkg in "$REPO_ROOT"/firmware/packages/fw_*/others/bcmdhd.ko; do
        [ -f "$pkg" ] || continue
        if [ "$(md5sum "$pkg" | awk '{print $1}')" = "$m" ]; then
            v=$(basename "$(dirname "$(dirname "$pkg")")" | sed 's/^fw_//')
            sources="$sources $v"
        fi
    done
    echo "  $m → $sources"
done
