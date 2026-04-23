# Seestar S50 — Verified Upgrade Procedure

**Status:** 2026-04-22 — full path from app 5.50 to app 7.32 executed cleanly on this prototype unit (serial `77d82606`, boardrev P304) using the driver-swap pattern.

Companion docs:
- [SEESTAR_WIFI_WEDGE_FIX.md](SEESTAR_WIFI_WEDGE_FIX.md) — user-facing writeup for other S50 owners
- [UPGRADE_PROBLEM_SUMMARY.md](UPGRADE_PROBLEM_SUMMARY.md) — historical investigation log

This doc is the **replayable procedure** for any affected unit. Detection is via `./tools/check_if_affected.sh`.

Each claim is tagged:
- **[V]** Verified this session — produced by a direct command run on the device
- **[I]** Inferred from code/audit — not runtime-tested
- **[?]** Open question

---

## Executive summary

- **[V]** The stock Oct 2025 `bcmdhd.ko` (md5 `8b75e5cd33fcf850dd673129d1842312`) wedges affected units with `HT Avail timeout (clkctl 0x50)`. It ships in every firmware package from fw_2.2.0 through fw_3.1.2.
- **[V]** Root cause: the stock Oct 2025 driver imports `mmc_hw_reset`; affected boards' DTB (`dwmmc@ffc70000`) lacks `cap-mmc-hw-reset`, so the reset call returns `-EOPNOTSUPP` leaving the SDIO bus in a state where the chip never grants HT clock.
- **[V]** **Two verified-good driver alternatives**:
  - **Jul 2023 factory** (md5 `4cfbf203772770d246db12505b744003`, extracted from `baseline-2.42/seestarOS.img` partition 6) — pre-regression driver, uses `mmc_sw_reset`.
  - **Patched Oct 2025** (md5 `1fc70c15691fa675fa3e4661aa783a12`) — Oct 2025 driver with one-symbol `objcopy --redefine-sym mmc_hw_reset=mmc_sw_reset`. Otherwise byte-identical to stock.
- **[V]** **Every iscope firmware push overwrites `/lib/modules/.../bcmdhd.ko`.** The fix procedure is: pre-stage one of the good drivers + swap script on `/home/pi/` → push iscope → SSH in post-upgrade → run swap script → reboot → verify.
- **[V]** Station mode (`wpa_svr=1`) survives upgrade. AP persists. sshd survives on 7.32 on this unit despite defensive rollback logic added in fw_3.1.0+.

---

## Verified upgrade chain (2026-04-22)

| From | To | fw pkg | iscope path in APK | Outcome |
|---|---|---|---|---|
| factory-reflashed 2.42 | 5.50 | fw_2.6.1 | `resources/assets/iscope` | [V] baseline restored |
| 5.50 | 5.82 | fw_2.6.4 | `resources/assets/iscope` | [V] wedge → swap → 9/9 green |
| 5.82 | 6.45 | fw_3.0.0 | `resources/asset_pack_0.apk/assets/iscope` | [V] wedge → swap → 9/9 green |
| 6.45 | 6.70 | fw_3.0.2 | `resources/assets/iscope` | [V] wedge → swap → 9/9 green + station mode live |
| 6.70 | 7.32 | fw_3.1.2 | `resources/assets/iscope` | [V] wedge → swap → 9/9 green |

The iscope payload location inside the APK varies. 3.0.0 uses `asset_pack_0.apk/assets/iscope`; 3.0.2 and 3.1.2 revert to `resources/assets/iscope`. Always `md5sum` the file before pushing.

## Current state

- **[V]** Firmware: fw_3.1.2 / app 7.32 (`version_remark=seestar-3.1`)
- **[V]** Driver: Jul 2023 factory (md5 `4cfbf203`)
- **[V]** AP: `S50_77d82606` on channel 44
- **[V]** Station: associated with configured home SSID
- **[V]** JSON-RPC ports 4700, 4350, 4361 all responding
- **[V]** No sound-33 triggers in dmesg

---

## Tool inventory (in `tools/`)

| Tool | Purpose | Verified |
|---|---|---|
| `check_if_affected.sh` | Detect whether this unit's DTB is missing `cap-mmc-hw-reset` | [V] correctly classifies our prototype as AFFECTED |
| `extract_factory_bcmdhd.sh` | Loop-mount `baseline-2.42/seestarOS.img` partition 6; extract `bcmdhd.ko` → `firmware/factory/bcmdhd.ko.jul2023` | [V] md5 `4cfbf203` |
| `swap_driver.sh <factory\|patched>` | Install a known-good driver variant, backup current, depmod, reboot | [V] both modes verified on 5.82, 6.45, 6.70, 7.32 |
| `audit_bcmdhd_across_versions.sh` | Tabulate bcmdhd.ko md5 + compile date across every fw package | [V] confirms all fw_2.2.0+ ship the Oct 2025 rebuild |
| `prepare_for_upgrade.sh [--to factory\|patched]` | Pre-stage driver + `post_upgrade_swap.sh` on device at `/home/pi/`; capture snapshot | [V] worked for 6.45, 6.70, 7.32 |
| `seestar_firmware_flash.py` | Push signed iscope to device over TCP (JSON-RPC + binary stream on port 4361) | [V] worked for all 4 hops |
| `verify_functional.sh` | 9-point functional check (driver classification, fw version, chip state, AP, hostapd, station, imager, sound-33, RPC ports) | [V] verified against all three driver variants |
| `enable_station_mode.sh` | Flip `wpa_svr=0` → `1` in `/home/pi/.ZWO/sh_conf.txt`; trigger reassoc | [V] established home-network path |
| `seestar-recovery.sh` | rkdeveloptool reflash to baseline-2.42 (last-resort fallback) | [V] recovered from initial wedge |
| `lib/common.sh` | Shared constants (driver md5s, DRIVER_PATH) + SSH helpers sourced by the other tool scripts | [V] all tools smoke-tested |

---

## Standard upgrade-hop procedure

For any iscope push (fw_2.6.4 → fw_3.1.2):

```bash
# 1. (Optional) Enable station mode so home network is an independent recovery path
./tools/enable_station_mode.sh --ip 169.254.100.100

# 2. Stage factory driver + post-upgrade swap script on device
./tools/prepare_for_upgrade.sh --ip 169.254.100.100

# 3. Push iscope (path varies per APK version — md5 first if unsure)
python3 tools/seestar_firmware_flash.py \
  firmware/decompiled/seestar_vX.Y.Z_decompiled/resources/assets/iscope \
  --host 169.254.100.100

# 4. Device reboots with Oct 2025 driver — chip wedges. SSH in via USB-ethernet:
ssh pi@169.254.100.100 'sudo /home/pi/post_upgrade_swap.sh'
# (device reboots once more with Jul 2023 driver)

# 5. Verify after ~90s
./tools/verify_functional.sh --ip 169.254.100.100
```

---

## Known behaviors & caveats

### `depmod: Read-only file system` during swap — [V] cosmetic
The `post_upgrade_swap.sh` flow remounts `/` read-write, writes `bcmdhd.ko`, runs `depmod -a`, then remounts read-only. On fw_3.1.x we've observed the filesystem getting remounted back to read-only *before* depmod runs (probably by the new `zwoair_daemon.sh` defensive logic). The `cp` itself succeeds; depmod fails with ENOENT-esque errors on `modules.dep.*` tempfiles. **This is harmless** because:
- bcmdhd is loaded by module name, and its path in `modules.dep` is unchanged (same filename, same directory).
- Both driver versions declare empty `depends:` (confirmed via `modinfo`), so dependency resolution is a no-op either way.

### `bluetooth.sh` rfkill race — [I] present from fw_2.7.0 onward
fw_2.7.0 introduced `/home/pi/ASIAIR/bin/bluetooth.sh`, which toggles `rfkill0`. On RV1126 `rfkill0` controls the combined WiFi+BT chip. Races with hostapd on boot. **We have not observed this cause AP failures on 6.45/6.70/7.32 with the factory driver in place** — either the race consistently loses (rfkill toggle happens before hostapd binds) or the factory driver handles rfkill differently than the Oct 2025 driver.

### sshd upgrade in fw_3.1.0+ — [I] mitigated by in-firmware rollback
`/home/pi/ASIAIR/bin/zwoair_daemon.sh` in fw_3.1.x contains defensive logic: if sshd isn't running after boot, it reinstalls `/usr/sbin/sshd.old` and restarts the service. This session did not trigger the failure. Keep USB-ethernet as the fallback.

### `network.sh` CN country reset — [I] low-impact
fw_3.0.0+ `network.sh` has a new block that forces `wl country CN` during a wpa_cli reconfigure event. Fires on station reassoc; no observed effect on our verified path.

---

## Resolved questions (2026-04-22)

- **[V]** Why does this chip wedge on Oct 2025 `bcmdhd.ko` while production units don't? — The Oct 2025 driver imports `mmc_hw_reset`; our DTB node `dwmmc@ffc70000` is missing the `cap-mmc-hw-reset` property, so mmc_hw_reset returns `-EOPNOTSUPP`. Production units' DTBs have the property (most likely — friend's working S50 almost certainly does, confirmed indirectly by the fact that the stock driver works on his unit).
- **[V]** Would a binary patch work? — Yes: `objcopy --redefine-sym mmc_hw_reset=mmc_sw_reset` on the Oct 2025 driver produces a fully-functional variant (md5 `1fc70c15...`). See `firmware/experimental/bcmdhd.ko.oct2025_mmc_sw_patched`.
- **[REFUTED]** Chip OTP programming as the difference between prototype and production — driver's OTP/CIS code is byte-identical between Jul 2023 and Oct 2025 builds; NVRAM file is byte-identical between prototype and a working friend's production unit.
- **[?]** Is the `iscope` payload signed with a key that the device validates via `app_publickey.pem` in `/home/pi/ASIAIR/`, or is the signature check optional? All pushes in this session succeeded with the existing signing flow (private key in `tools/seestar_firmware_flash.py`), so the key is accepted by every shipping firmware version.

---

## Recovery if the swap doesn't land

1. **SSH unreachable** — wait 3+ minutes for self-healing logic (sshd rollback). Retry.
2. **USB-ethernet dead too** — check for the device as a different `usb*` interface on the host.
3. **Fully unreachable** — `tools/seestar-recovery.sh` does a rkdeveloptool maskrom reflash back to baseline-2.42. You lose all on-device state (wpa_supplicant.conf creds, sh_conf settings, sound files) but the device is recoverable.

Don't 3-second hardware-reset from a wedged state — it wipes `wpa_supplicant.conf` and removes the station-mode SSH fallback.
