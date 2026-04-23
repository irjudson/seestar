# Seestar S50 — Firmware Analysis, Wi-Fi Wedge Fix & Recovery

Tooling and analysis around the ZWO Seestar S50 smart telescope: protocol
reverse-engineering, firmware extraction/diff/patching, license generation,
recovery workflows, and — now-resolved — the Wi-Fi chip wedge that affects
a cohort of units upgrading past app 5.82.

> **Disclaimer.** This project is not affiliated with, endorsed by, or
> sponsored by ZWO. It is independent reverse-engineering and repair
> tooling developed on a personally-owned device. The bcmdhd kernel
> module whose behaviour is discussed here is GPL-licensed. Using any
> of the tools or patches described may void your device warranty and
> could change how the device interacts with future official updates.
> Use at your own risk. See [CONTRIBUTING.md](CONTRIBUTING.md) to report
> additional affected units or contribute test data.

## Canonical docs

- **[SEESTAR_WIFI_WEDGE_FIX.md](SEESTAR_WIFI_WEDGE_FIX.md)** — user-facing
  writeup of the bug and the 1-symbol fix. Paste-ready for a forum / gist;
  this is what other affected S50 owners should read.
- **[UPGRADE_PROCEDURE_VERIFIED.md](UPGRADE_PROCEDURE_VERIFIED.md)** —
  step-by-step replayable procedure for upgrading an affected unit 5.50 → 7.32.
- **[UPGRADE_PROBLEM_SUMMARY.md](UPGRADE_PROBLEM_SUMMARY.md)** — the
  investigation log (`[V]` verified / `[I]` inferred / `[?]` open tags).
  Historical record of every hypothesis we explored, most of which were
  refuted.
- **[HACKING.md](HACKING.md)** — short orientation card.

## Status (2026-04-22)

**Root cause identified and fix verified end-to-end** across every firmware
version from 5.50 (fw_2.6.1) to 7.32 (fw_3.1.2).

| Question | Answer |
|---|---|
| What's broken? | Oct 2025 rebuild of `bcmdhd.ko` imports `mmc_hw_reset`. The RV1126 dwmmc controller on the S50 doesn't advertise `cap-mmc-hw-reset`, and on a subset of chips the resulting behaviour leaves the SDIO bus wedged at `HT Avail timeout (clkctl 0x50)`. Why only some S50s wedge is still unresolved — the DTB state is identical across working and broken units. |
| What's the fix? | `objcopy --redefine-sym mmc_hw_reset=mmc_sw_reset` on the driver — one-symbol ELF patch, no kernel rebuild. |
| How do I diagnose my S50? | `./tools/wifi-driver-check.sh --ip <seestar-ip>` |
| How do I fix my unit? | `./tools/swap_driver.sh patched --ip <seestar-ip>` |

## Quick-start (affected device)

```bash
# 1. What's running on this unit, and is it wedged?
./tools/wifi-driver-check.sh --ip 169.254.100.100

# 2. Install the patched driver
./tools/swap_driver.sh patched --ip 169.254.100.100
# → reboots device

# 3. Verify everything came up clean
./tools/verify_functional.sh --ip 169.254.100.100
```

## Quick-start (upgrading an affected device)

```bash
# 1. Stage the patched driver + post-upgrade recovery script on the device
./tools/prepare_for_upgrade.sh --to patched --ip 169.254.100.100

# 2. Push the new firmware with your upgrade tool (iscope will overwrite
#    the driver with the stock Oct 2025 broken variant — expected)
python3 tools/seestar_firmware_flash.py \
    --host 169.254.100.100 \
    firmware/decompiled/seestar_v3.1.2_decompiled/resources/assets/iscope

# 3. After the device wedges, SSH in and trigger the pre-staged recovery
ssh pi@169.254.100.100 'sudo /home/pi/post_upgrade_swap.sh'

# 4. Verify after reboot (~90s)
./tools/verify_functional.sh --ip 169.254.100.100
```

## Repo layout

```
tools/                        Active CLI utilities (see table below)
tools/lib/common.sh           Shared constants + SSH helpers for tool scripts
tools/desktop-setup/          Host-side udev rules for USB-ethernet auto-config
analysis/output/              Written investigation reports (markdown)
analysis/driver_diff/         Symbol/string diffs between the two bcmdhd builds
analysis/ghidra_diff/scripts/ Our Ghidra scripts (ZWO binaries themselves are not shipped)
analysis/src/                 Analysis tooling (APK downloader, etc.)
```

The Python client library has moved to its own repo:
**https://github.com/irjudson/seestar-api**

The following paths are **not included** in this repo (gitignored); the
tools regenerate or extract what they need on demand:

```
firmware/packages/            ZWO firmware bundles — copyright ZWO
firmware/decompiled/          jadx output of ZWO APKs — copyright ZWO
firmware/signed/              Pre-signed iscope files
firmware/factory/             Extracted factory driver (re-extract via tools/extract_factory_bcmdhd.sh)
firmware/experimental/        Built artifacts (patched .ko — rebuild per SEESTAR_WIFI_WEDGE_FIX.md)
baseline-2.42/seestarOS.img   Factory image for rkdeveloptool recovery
s50-fs/                       Your device filesystem snapshot
apks/                         ZWO APK archive — copyright ZWO
analysis/jadx/                Decompiled APK contents — copyright ZWO
analysis/ghidra_diff/binaries Extracted ZWO binaries
analysis/ghidra_diff/out*/    Ghidra decompilation output
analysis/fw_5.82_failure_dmesg/ Device-specific capture (contains ZWO binaries too)
```

The Python client library lives at [github.com/irjudson/seestar-api](https://github.com/irjudson/seestar-api).

## Tools

### Driver + upgrade workflow

| Tool | Purpose |
|---|---|
| `wifi-driver-check.sh` | Fingerprint bcmdhd.ko + scan dmesg; emit `FACTORY_SAFE` / `PATCHED_SAFE` / `WEDGED_NOW` / `REGRESSED_AT_RISK` / `UNKNOWN_DRIVER` verdict |
| `swap_driver.sh <factory\|patched>` | Install a known-good driver variant and reboot |
| `prepare_for_upgrade.sh [--to factory\|patched]` | Stage driver + post-upgrade recovery script before pushing firmware |
| `verify_functional.sh` | 9-point health check (driver classification, chip state, AP, hostapd, station, imager, sound-33, RPC ports) |
| `audit_bcmdhd_across_versions.sh` | Tabulate bcmdhd.ko md5 + compile date across every fw package |
| `extract_factory_bcmdhd.sh` | Extract the Jul 2023 driver from `baseline-2.42/seestarOS.img` |

### Firmware push / recovery

| Tool | Purpose |
|---|---|
| `seestar_firmware_flash.py` | Push signed iscope to the device via JSON-RPC on ports 4350/4361 |
| `sign_firmware.py` | SHA-1 + RSA PKCS1v15 sign a tar.bz2 as an iscope |
| `seestar-recovery.sh` | Last-resort rkdeveloptool maskrom reflash + post-flash setup |
| `extract_firmware.py` | Extract fw package bundles |

### On-device config

| Tool | Purpose |
|---|---|
| `install_license_rpc.py` | Install license via `pi_encrypt` RPC (no SSH required) |
| `get_license.py` | Fetch a valid license from `api.seestar.com/v1/activation` |
| `set_wifi_country.py` | Send `set_wifi_country` RPC |
| `enable_station_mode.sh` | Flip `wpa_svr=1` + trigger home-network reassoc |
| `usb_ether_fix.sh` | On-device: unwedge dwc3 gadget, reload g_ether |

### Shared

| Tool | Purpose |
|---|---|
| `lib/common.sh` | SSH setup, driver md5 constants, `DRIVER_PATH`, pass/fail print helpers |
| `desktop-setup/` | Linux udev rule + helper to bring up a Seestar USB-ethernet interface on the host |

## Three known driver fingerprints (`bcmdhd.ko`)

| md5 | Compile | Behavior | Source |
|---|---|---|---|
| `4cfbf203772770d246db12505b744003` | Jul 7 2023 | Verified working | baseline-2.42 seestarOS.img partition 6 |
| `1fc70c15691fa675fa3e4661aa783a12` | Oct 17 2025 | Verified working | objcopy `mmc_hw_reset→mmc_sw_reset` patch of stock Oct 2025 |
| `8b75e5cd33fcf850dd673129d1842312` | Oct 17 2025 | **Wedges affected units** | Ships in every fw_2.6.4+ package |

## Hardware notes

- SoC: Rockchip RV1126, 32-bit ARM (armhf), kernel 4.19.111
- WiFi/BT: Broadcom BCM43456 (Ampak AP6256 module), `bcmdhd.ko` driver, `WL_REG_ON=-1` (no GPIO reset)
- Boot partition: eMMC with GPT, factory image `baseline-2.42/seestarOS.img`
- UART: J2 pads near ESP32, 1.8V logic, 1500000 baud — kernel output only, no getty
- USB-C: dwc3 gadget, defaults to g_mass_storage; switches to g_ether when `/home/pi/en_eth=1`
