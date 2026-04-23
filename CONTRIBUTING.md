# Contributing to the Seestar repo

Thanks for your interest. This repository holds independent
reverse-engineering and repair tooling for the ZWO Seestar S50 smart
telescope. The primary deliverable is the Wi-Fi driver wedge fix
documented in [SEESTAR_WIFI_WEDGE_FIX.md](SEESTAR_WIFI_WEDGE_FIX.md).

## What this project is (and isn't)

- **Is**: diagnostics, a verified fix for the Oct 2025 `bcmdhd.ko`
  regression on affected S50 units, plus the supporting tooling
  (detection, driver swap, upgrade prep, verification, and recovery).
- **Isn't**: affiliated with ZWO, a replacement for the official app,
  a redistribution of ZWO's firmware or APK content, or a tool for
  unauthorised firmware modification.

## What's most valuable to contribute

### 1. Affected-unit data points

If you have an S50 and run `./tools/wifi-driver-check.sh`, please file
an issue with:

- Verdict line (`FACTORY_SAFE` / `PATCHED_SAFE` / `WEDGED_NOW` /
  `REGRESSED_AT_RISK` / `UNKNOWN_DRIVER`)
- Device serial (last 8 of `Serial:` from `/proc/cpuinfo` — publicly
  visible in your AP SSID anyway)
- Board revision (from `sudo dmesg | grep boardrev` — e.g. `P304`)
- Current ZWO firmware version (`version_string` from `/home/pi/ASIAIR/config`)
- Approximate ship date, if you know it

The cohort differentiator is still open (see UPGRADE_PROBLEM_SUMMARY.md);
`REGRESSED_AT_RISK` reports — units running the stock Oct 2025 driver
*without* wedging — are particularly valuable for narrowing down which
boards are actually susceptible.

### 2. Confirm the fix works on your unit

If you applied the patched driver (via `./tools/swap_driver.sh patched`
or the manual `objcopy` path documented in SEESTAR_WIFI_WEDGE_FIX.md),
let us know whether `./tools/verify_functional.sh` returns all green
and `./tools/wifi-driver-check.sh` prints `PATCHED_SAFE`. Negative
results are just as valuable as positive ones.

### 3. Tool bugs / improvements

Scripts here should work on any affected S50. If one breaks on your
configuration, file an issue with:

- The command you ran (exact)
- Full output (or the relevant error)
- Your device's firmware version
- Whether the device was reachable via USB-ethernet or WiFi at the time

### 4. Better documentation

If something in the writeup is unclear, wrong, or assumes knowledge
that isn't obvious, PRs against the docs are welcome. Particularly
useful: clarifications for owners who haven't used `ssh`, `scp`, or
`objcopy` before.

## What we won't accept

- **Signed firmware bundles** or derivatives of ZWO's compiled
  binaries (the `bcmdhd.ko` itself, hostapd, wpa_supplicant,
  zwoair_imager, etc). Users extract their own copies from their
  device or from a ZWO APK they already possess.
- **ZWO RSA private keys**, license files, or anything that would
  leak ZWO proprietary keys.
- **Decompiled ZWO source code.** Our analysis commentary is
  welcome; redistributing ZWO's code is not.
- **"Fixes" that weaponise the driver-swap procedure** (e.g. payload
  delivery, persistent rootkits, backdoors). The procedure and tools
  here are for recovering *your own* device.

## Code style

- Shell scripts: `bash`, `set -e` where practical, source
  `tools/lib/common.sh` for constants and SSH/print helpers
- Python: 3.10+, stdlib-preferred, standard argparse for CLIs
- One purpose per tool; keep scripts composable

## Reporting security issues

If you find a way the tools here leak private data (SSIDs,
passphrases, keys) when run by another user, please open a private
security advisory on GitHub rather than a public issue.
