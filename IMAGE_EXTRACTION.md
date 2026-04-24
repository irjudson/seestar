# Seestar S50 — Device Image Extraction

How to capture a current-state `seestarOS.img` directly from a running S50,
replacing the old `baseline-2.42/seestarOS.img` (donor unit, vintage Apr 2024)
with a fresh image from your own device.

## Why

The `baseline-2.42/seestarOS.img` is from a different unit (ap_id `3731a279`,
factory-tested Jan 2024). It works as a recovery baseline but is two years stale:
it predates the ASCOM Alpaca server, all AI model files, and several firmware
updates. An image captured from a fully-upgraded unit gives you a recovery baseline
that boots straight to the current app version with no upgrade chain needed.

## What's captured

Partitions p1–p7 (~9.7 GB raw, ~3–4 GB compressed):

| Partition | Size | Contents |
|---|---|---|
| p1 | 4 MB | U-Boot SPL |
| p2 | 4 MB | U-Boot env |
| p3 | 64 MB | Kernel + DTB |
| p4 | 32 MB | Recovery kernel |
| p5 | 512 MB | `/home/pi` (ext4) |
| p6 | 5 GB | rootfs (ext4) |
| p7 | 2 GB | swap |
| p8 | 50.6 GB | **Skipped** |

p8 (Seestar image storage, exFAT) is skipped entirely. `rc.local` auto-formats
it on first boot if it is absent or not exFAT, so no data is lost.

## Extraction

Three capture modes, all output to `baseline-current/seestarOS-<date>-<serial>.img.gz`.

### SSH over USB-ethernet (recommended — fastest, ~4 min)

Device must be running normally with USB-C connected to the host.

```bash
./tools/extract_device_image.sh --ssh-usb
```

Uses the fixed gadget IP `169.254.100.100`. The script remounts the rootfs
read-only for the duration of the `dd`, then restores read-write immediately
after.

### SSH over WiFi / LAN

```bash
./tools/extract_device_image.sh --ssh-wifi --ip 192.168.2.47
```

Same as USB mode, slower (~8–16 min depending on WiFi throughput).

### rkdeveloptool USB ReadLBA (~30–40 min)

Requires the device to be in **loader or maskrom mode**:

1. Power the device off
2. Hold the small recovery button (near the USB-C port)
3. While holding, connect USB-C to the host
4. Release after ~2 seconds
5. Confirm detection: `sudo rkdeveloptool ld`  → should show `Loader` or `MaskRom`

```bash
sudo ./tools/extract_device_image.sh --rkdeveloptool
```

If the device is in MaskRom mode the script loads the SPL automatically before
reading. If it's already in Loader mode it reads directly.

## Verification

Run the static verifier before trusting the image for reflash:

```bash
sudo bash tools/verify_extracted_image.sh baseline-current/seestarOS-*.img.gz
```

Checks performed:

| Check | What it validates |
|---|---|
| GPT partition table | 8 partitions present, p6 at correct sector offset |
| p6 mounts as ext4 | rootfs is a valid filesystem |
| p5 mounts as ext4 | `/home/pi` is a valid filesystem |
| bcmdhd.ko md5 | Classifies against known-good fingerprint table |
| rc.local present | Boot script exists |
| WiFi firmware blob | `fw_bcm43752a2_ag.bin` present |
| nvram_ap6256.txt | NVRAM present |
| ap_id check | Flags if donor unit ID (`3731a279`) is present |
| ap_id_inited | Warns if set to `true` (SSID will NOT regenerate on reflash to a different unit) |
| ASIAIR app version | Reports the captured app version |
| Not-identical-to-baseline | Confirms capture differs from the old 2.42 image |

The ultimate test is a live flash (see below).

## What differs from baseline-2.42

A byte-level comparison between the 2.42 image and a current S50 filesystem
snapshot confirmed the following are **identical**: kernel, DTBs, rc.local, all
WiFi firmware blobs, nvram_ap6256.txt, all non-updated kernel modules, modprobe.d
configs, systemd units, and network config.

The following are **different** (expected — reflect newer firmware):

- ASIAIR app scripts (asiair.sh, network.sh, common.sh, etc.)
- `/etc/zwo/ai_model/` — 15 RKNN neural network models (added post-2.42)
- `/etc/zwo/Alpaca/` — ASCOM Alpaca server stack (added post-2.42)
- `/etc/zwo/zwo_iscope_update_v2271` vs `v2158`
- `/usr/bin/updateEngine`
- `/etc/dhcpcd.conf` — uap0 stanza gains `noarp` + `nodhcp`
- Per-unit config in `/home/pi/.ZWO/` and `/home/pi/AP_*.conf`

The `bcmdhd.ko` in a current image will be the **Oct 2025 stock driver**
(md5 `8b75e5cd...`) unless you have already applied the patched driver.
See the note below.

## Flashing the captured image

```bash
# Decompress (requires ~9.7 GB free)
zcat baseline-current/seestarOS-<date>-<serial>.img.gz > /tmp/seestarOS-current.img

# Device must be in loader/maskrom mode (see above)
sudo rkdeveloptool db baseline-2.42/rkdeveloptool/rk356x_spl_loader_v1.13.112.bin
sudo rkdeveloptool wl 0 /tmp/seestarOS-current.img
sudo rkdeveloptool rd
```

After first boot (~2 min):

```bash
# Fix ap_id if flashing to a different unit than the source
bash tools/seestar-recovery.sh --pre-upgrade --ip 169.254.100.100

# Confirm bcmdhd.ko state
./tools/wifi-driver-check.sh --ip 169.254.100.100
```

If the image was captured from a device running the Oct 2025 stock driver, install
the patched driver immediately after confirming SSH access:

```bash
./tools/swap_driver.sh patched --ip 169.254.100.100
```

## ap_id note

If the source and target device are the **same unit**, `ap_id_inited=true` in the
captured image is correct — the unit will keep its own SSID.

If flashing to a **different unit**, set `ap_id_inited=false` in
`/home/pi/.ZWO/ASIAIR_general.xml` before flashing (or run
`tools/seestar-recovery.sh --pre-upgrade` after first boot), otherwise the target
device will boot with the source unit's SSID.
