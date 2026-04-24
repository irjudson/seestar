#!/bin/bash
# Extract a current seestarOS.img from an S50 — three capture modes:
#
#   --ssh-usb          SSH over USB-ethernet gadget (169.254.100.100)  [default]
#   --ssh-wifi         SSH over WiFi/LAN (requires --ip <address>)
#   --rkdeveloptool    USB ReadLBA while device is in loader/maskrom mode
#
# Output: a gzipped raw disk image containing GPT + p1–p7 (~9.7 GB raw,
#         ~3-4 GB compressed). Skips p8 (50.6 GB image storage) — rc.local
#         auto-formats it as exFAT on first boot.
#
# The image is directly flashable with rkdeveloptool wl 0.
#
# Usage:
#   ./tools/extract_device_image.sh [--ssh-usb | --ssh-wifi | --rkdeveloptool]
#                                   [--ip <address>]  (wifi mode)
#                                   [--out <file.img.gz>]
#
# For --rkdeveloptool:
#   1. Power off the device
#   2. Hold the recovery button, connect USB-C to your host
#   3. Release button once rkdeveloptool detects the device
#   4. Run this script as sudo (rkdeveloptool needs raw USB access)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RKDEV="$REPO_ROOT/baseline-2.42/rkdeveloptool/rkdeveloptool"
LOADER="$REPO_ROOT/baseline-2.42/rkdeveloptool/rk356x_spl_loader_v1.13.112.bin"

# ── Partition layout (sectors, 512 bytes each) ──────────────────────
# p1:   16384 –   24575   (4 MB)   U-Boot SPL
# p2:   24576 –   32767   (4 MB)   U-Boot env
# p3:   32768 –  163839  (64 MB)   kernel / dtb
# p4:  163840 –  229375  (32 MB)   recovery kernel
# p5:  229376 – 1277951 (512 MB)   /home/pi  (ext4)
# p6: 1277952 –11763711  (5 GB)    rootfs    (ext4)
# p7: 11763712–15958015  (2 GB)    swap
# p8: 15958016–122159040 (50.6 GB) Seestar storage — SKIPPED
CAPTURE_END=20152320   # = 15958016 + 4194304 (end of p7)
SECTOR_SIZE=512

# ── Colour helpers ──────────────────────────────────────────────────
if [ -t 1 ]; then
    R="\033[31m" G="\033[32m" Y="\033[33m" B="\033[34m" W="\033[0m"
else R="" G="" Y="" B="" W=""; fi
pass() { printf "  ${G}✓${W} %s\n" "$1"; }
fail() { printf "  ${R}✗${W} %s\n" "$1" >&2; }
warn() { printf "  ${Y}!${W} %s\n" "$1"; }
info() { printf "    %s\n" "$1"; }
hr()   { printf "${B}══════════════════════════════════════════════════════════${W}\n"; }

# ── Parse args ──────────────────────────────────────────────────────
MODE="ssh-usb"
IP="169.254.100.100"
OUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ssh-usb)       MODE="ssh-usb";       shift ;;
        --ssh-wifi)      MODE="ssh-wifi";       shift ;;
        --rkdeveloptool) MODE="rkdeveloptool";  shift ;;
        --ip)            IP="$2";               shift 2 ;;
        --out)           OUT_FILE="$2";         shift 2 ;;
        *) shift ;;
    esac
done

# ssh-usb uses the fixed gadget IP; ssh-wifi uses --ip
[ "$MODE" = "ssh-usb" ] && IP="169.254.100.100"

SSH_CMD="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
             -o ServerAliveInterval=30 -o ServerAliveCountMax=4 pi@${IP}"

# ── Pre-flight ───────────────────────────────────────────────────────
hr
printf "  ${B}Seestar S50 — filesystem image extractor${W}\n"
hr
echo ""
info "Mode: $MODE"
CAPTURE_MB=$(( CAPTURE_END * SECTOR_SIZE / 1024 / 1024 ))
info "Capture range: sectors 0–${CAPTURE_END} (${CAPTURE_MB} MB, p1–p7)"
echo ""

case "$MODE" in
# ════════════════════════════════════════════════════════════════════
ssh-usb|ssh-wifi)
# ════════════════════════════════════════════════════════════════════

    info "Target: pi@${IP}"
    if ! $SSH_CMD 'true' 2>/dev/null; then
        fail "Cannot reach pi@${IP}"
        if [ "$MODE" = "ssh-usb" ]; then
            info "Check: USB-C cable connected, device is running (not in maskrom)"
            info "       USB gadget mode requires the device to be fully booted"
        else
            info "Check: --ip address correct, device on same network"
        fi
        exit 1
    fi
    pass "SSH reachable"

    # Gather identity for the output filename
    # ap_id matches the SSID (S50_<ap_id>) and is the recognisable device identifier
    SERIAL=$($SSH_CMD 'grep -m1 ssid /home/pi/AP_2.4G.conf 2>/dev/null | cut -d_ -f2' \
        2>/dev/null | tr -d '\r\n ' || echo "unknown")
    [ -z "$SERIAL" ] && \
        SERIAL=$($SSH_CMD 'cat /proc/cpuinfo | grep Serial | awk "{print \$3}"' \
            2>/dev/null | tr -d '\r\n ' | tail -c8 || echo "unknown")
    FW_VER=$($SSH_CMD 'head -1 /home/pi/ASIAIR/bin/Soft03Cmt.txt 2>/dev/null' \
        2>/dev/null | tr -d '\r\n' || echo "unknown")
    DATE_STR=$(date +%Y%m%d)
    [ -z "$OUT_FILE" ] && \
        OUT_FILE="${REPO_ROOT}/baseline-current/seestarOS-${DATE_STR}-${SERIAL}.img.gz"

    info "Device serial:   ${SERIAL}"
    info "Firmware:        ${FW_VER}"
    info "Output:          ${OUT_FILE}"
    echo ""

    mkdir -p "$(dirname "$OUT_FILE")"

    # Remount rootfs read-only for snapshot consistency
    warn "Remounting rootfs read-only for cleaner snapshot..."
    $SSH_CMD 'sudo mount -o remount,ro / 2>/dev/null' && \
        pass "rootfs remounted ro" || \
        warn "Could not remount ro — proceeding live (safe for recovery use)"
    echo ""

    BLOCK_COUNT=$(( CAPTURE_END / 8 ))   # 4M blocks (8 sectors each)
    pass "Streaming ${CAPTURE_MB} MB over SSH → gzip (expect 10–25 min)..."
    echo ""
    $SSH_CMD \
        "sudo dd if=/dev/mmcblk0 bs=4M count=${BLOCK_COUNT} status=progress 2>&1 | \
         grep -E 'bytes|copied' >&2 ; \
         sudo dd if=/dev/mmcblk0 bs=4M count=${BLOCK_COUNT} 2>/dev/null" \
        | gzip -1 > "$OUT_FILE"

    # Restore rw
    $SSH_CMD 'sudo mount -o remount,rw / 2>/dev/null' && \
        pass "rootfs remounted rw" || true
    ;;

# ════════════════════════════════════════════════════════════════════
rkdeveloptool)
# ════════════════════════════════════════════════════════════════════

    # Build rkdeveloptool if needed
    if [ ! -x "$RKDEV" ]; then
        warn "rkdeveloptool not built — building now..."
        (cd "$REPO_ROOT/baseline-2.42/rkdeveloptool" && \
         autoreconf -i 2>/dev/null && ./configure 2>/dev/null && make -j4 2>/dev/null) && \
            pass "Built OK" || { fail "Build failed — see baseline-2.42/rkdeveloptool/"; exit 1; }
    fi

    # Check device is present
    if ! $RKDEV ld 2>/dev/null | grep -qiE "loader|maskrom"; then
        fail "No device in loader/maskrom mode detected"
        echo ""
        info "To enter loader mode:"
        info "  1. Power off the S50"
        info "  2. Hold the small recovery button (near USB-C port)"
        info "  3. While holding, connect USB-C to this machine"
        info "  4. Release after 2 seconds"
        info "  5. Run: sudo $RKDEV ld    (should show Loader or MaskRom)"
        exit 1
    fi
    pass "Device detected in loader/maskrom mode"

    # If maskrom, load the SPL loader first
    if $RKDEV ld 2>/dev/null | grep -qi "maskrom"; then
        warn "MaskRom mode — loading SPL first..."
        if [ ! -f "$LOADER" ]; then
            fail "Loader binary not found: $LOADER"
            exit 1
        fi
        $RKDEV db "$LOADER" && pass "SPL loaded" || { fail "db failed"; exit 1; }
        sleep 2
    fi

    DATE_STR=$(date +%Y%m%d)
    RAW_FILE="${REPO_ROOT}/baseline-current/seestarOS-${DATE_STR}-rkusb.img"
    [ -z "$OUT_FILE" ] && OUT_FILE="${RAW_FILE}.gz"
    mkdir -p "$(dirname "$OUT_FILE")"

    info "Output:     ${OUT_FILE}"
    echo ""
    pass "Reading ${CAPTURE_MB} MB via ReadLBA (expect 20–40 min)..."
    echo ""

    # rkdeveloptool rl reads in one shot — no streaming, writes to file
    $RKDEV rl 0 "$CAPTURE_END" "$RAW_FILE" && pass "Read complete" || \
        { fail "rkdeveloptool rl failed"; exit 1; }

    pass "Compressing..."
    gzip -1 "$RAW_FILE" && mv "${RAW_FILE}.gz" "$OUT_FILE"
    ;;

*)
    fail "Unknown mode: $MODE"
    exit 1
    ;;
esac

# ── Patch GPT alternate-LBA ──────────────────────────────────────────
# The GPT backup header lives at the last sector of the full 62GB disk.
# Since we only captured through p7, the backup is absent. Patch the
# primary header's alternate-LBA to match the truncated size so that
# fdisk/parted don't report a corrupt GPT. rkdeveloptool ignores this.
warn "Patching GPT alternate-LBA for truncated image..."
python3 - "$OUT_FILE" "$CAPTURE_END" <<'PYEOF'
import sys, gzip, struct, zlib, os

path = sys.argv[1]
capture_end = int(sys.argv[2])
HEADER_BYTES = 34 * 512
CHUNK = 4 * 1024 * 1024

with gzip.open(path, 'rb') as f:
    data = bytearray(f.read(HEADER_BYTES))

GPT_HDR = 512
if data[GPT_HDR:GPT_HDR+8] != b'EFI PART':
    print(f"  Warning: GPT signature not found — skipping patch")
    sys.exit(0)

# Patch alternate LBA (offset 32 in GPT header, 8 bytes LE)
struct.pack_into('<Q', data, GPT_HDR + 32, capture_end - 1)

# Patch last usable LBA (offset 40 in GPT header, 8 bytes LE) to match
struct.pack_into('<Q', data, GPT_HDR + 40, capture_end - 34)

# Recalculate header CRC32
hdr_size = struct.unpack_from('<I', data, GPT_HDR + 12)[0]
struct.pack_into('<I', data, GPT_HDR + 16, 0)
crc = zlib.crc32(bytes(data[GPT_HDR:GPT_HDR + hdr_size])) & 0xFFFFFFFF
struct.pack_into('<I', data, GPT_HDR + 16, crc)

# Stream: emit patched header then the rest of the decompressed image in chunks.
# Never loads the full image into RAM.
tmp = path + '.gpt_patch.tmp'
with gzip.open(path, 'rb') as fin:
    fin.read(HEADER_BYTES)          # discard original header bytes
    with gzip.open(tmp, 'wb', compresslevel=1) as fout:
        fout.write(bytes(data))     # write patched header
        while True:
            chunk = fin.read(CHUNK)
            if not chunk:
                break
            fout.write(chunk)

os.replace(tmp, path)
print("  GPT patched OK")
PYEOF

# ── Final report ────────────────────────────────────────────────────
echo ""
FINAL_SIZE=$(du -h "$OUT_FILE" | awk '{print $1}')
hr
pass "Image saved: $OUT_FILE ($FINAL_SIZE)"
echo ""
info "Verify partition table:"
info "  zcat '$OUT_FILE' | fdisk -l -"
echo ""
info "Flash to a device in loader/maskrom mode:"
info "  zcat '$OUT_FILE' > /tmp/seestarOS-current.img"
info "  sudo rkdeveloptool db '$LOADER'"
info "  sudo rkdeveloptool wl 0 /tmp/seestarOS-current.img"
info "  sudo rkdeveloptool rd"
echo ""
info "After first boot, fix the ap_id:"
info "  bash tools/seestar-recovery.sh --pre-upgrade --ip <device-ip>"
hr
