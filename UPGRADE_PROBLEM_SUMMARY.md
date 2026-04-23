# Seestar S50 Firmware Upgrade — Investigation Log

> **Superseded by** [SEESTAR_WIFI_WEDGE_FIX.md](SEESTAR_WIFI_WEDGE_FIX.md)
> (user-facing fix writeup) and
> [UPGRADE_PROCEDURE_VERIFIED.md](UPGRADE_PROCEDURE_VERIFIED.md)
> (replayable upgrade procedure). Preserved here as the historical record
> of the hypotheses considered (and mostly refuted) during the investigation.

## Final conclusion (2026-04-22, amended 2026-04-23)

The 5.82+ chip wedge traces to the Oct 17 2025 rebuild of `bcmdhd.ko`
(md5 `8b75e5cd…`), which imports `mmc_hw_reset` where the July 2023
factory driver (md5 `4cfbf203…`) imports `mmc_sw_reset`. On this
unit's SDIO bus, the `mmc_hw_reset` call leaves the chip unable to
grant HT clock, and chip init hangs at `HT Avail timeout (clkctl
0x50)`.

A one-symbol ELF patch (`objcopy --redefine-sym mmc_hw_reset=mmc_sw_reset`)
on the Oct 2025 driver produces md5 `1fc70c15…`, which is verified
functional on this unit across every firmware from 5.50 to 7.32.

**Amendment (2026-04-23):** initially we believed the DTB state
(`dwmmc@ffc70000` missing `cap-mmc-hw-reset`) was the cohort
differentiator — i.e., only DTBs lacking the property would be
affected. Field reports from other S50 owners then showed two working
units on the Oct 2025 driver whose DTBs *also* lack the property.
Every S50 sampled so far has the identical DTB state, working and
broken alike. So the DT absence is a necessary-but-not-sufficient
condition; the per-unit gate for whether `mmc_hw_reset` actually
wedges the chip is still open (chip stepping / SDIO timing / board
revision are plausible, none confirmed). The patched driver side-steps
the question by not calling `mmc_hw_reset` at all.

All other hypotheses in this document — NVRAM differences, chip OTP
programming, hostapd/wpa_supplicant regressions, bluetooth.sh rfkill
races, mount MCU firmware triggers, country-code priming — were
investigated and **refuted**. They appear in this log for completeness.

---

## Original problem statement (preserved verbatim below)

**Status as of 2026-04-22:** Root cause of the 5.82+ chip wedge **identified and verified**: the `bcmdhd.ko` shipped by fw_2.6.4 through fw_3.1.2 (build date Oct 17 2025, md5 `8b75e5cd…`) regresses on this S50 chip versus the factory driver (build date Jul 7 2023, md5 `4cfbf203…`) baked into `baseline-2.42/seestarOS.img`. Pushing 5.82 firmware but substituting the Jul 2023 driver produces a fully working 5.82 with **zero HT Avail timeouts**.

Each claim in this document is tagged with one of:
- **[V]** Verified — we ran a command that directly produced the result
- **[I]** Inferred — deduced from code/docs but not runtime-tested
- **[?]** Open question — stated for completeness, not confirmed

---

## Device

- **[V]** Hardware: ZWO Seestar S50, "ZWO SeeStar Board V0.1 (Rockchip-RV1126-Linux)" — from `dmesg: OF: fdt: Machine model`
- **[V]** SoC: Rockchip RV1126, 32-bit ARM, kernel 4.19.111 — from `uname`
- **[V]** WiFi/BT chip: BCM43456 (AP6256) — SDIO F1 signature `0x15294345`, `chip:0x4345 rev:0x9 pkg:0x2`, `boardrev P304` per `wl revinfo`
- **[V]** Driver: `bcmdhd.ko` in `/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/`
- **[V]** WL_REG_ON GPIO = `-1` (no software-controlled reset for WiFi chip) — from dmesg
- **[V]** CPU serial last 8: `77d82606`

---

## THE ROOT CAUSE (verified 2026-04-22)

### Finding [V]

**Two distinct `bcmdhd.ko` binaries exist in the repo:**

| Source | MD5 | Compile string | Chip behavior |
|--------|-----|---------------|---------------|
| `baseline-2.42/seestarOS.img` (factory; extracted via loop-mount of partition 6) | `4cfbf203772770d246db12505b744003` | `compiled on Jul  7 2023 at 17:01:04` | ✅ works on this chip (0 HT Avail timeouts on 5.82) |
| fw_2.2.0 through fw_3.1.2 `others/bcmdhd.ko` (all identical to each other) | `8b75e5cd33fcf850dd673129d1842312` | `compiled on Oct 17 2025 at 16:52:35` | ❌ wedges this chip (HT Avail timeout every retry) |

Both drivers report the same upstream DHD version string `101.10.361.29 (wlan=r892223-20221214-2)`. The Oct 2025 rebuild is a newer compile of what appears to be the same Broadcom source, but with different behavior on this chip.

### Verification [V]

1. `tools/extract_factory_bcmdhd.sh` — loop-mounts baseline-2.42 p6, extracts bcmdhd.ko, saves to `firmware/factory/bcmdhd.ko.jul2023`, reports `md5=4cfbf203…` and compile date `Jul 7 2023`
2. `tools/audit_bcmdhd_across_versions.sh` — md5sums every fw_*/others/bcmdhd.ko; all are `8b75e5cd…` Oct 17 2025
3. `tools/swap_bcmdhd_to_factory.sh` — on a device running fw_2.6.4 (5.82) WEDGED with HT Avail timeouts, replaced the Oct 2025 driver with the Jul 2023 driver, rebooted. Result: chip came up with **0 HT Avail timeouts**, `wl country` returned `US (US/988) UNITED STATES`, wlan0 `UP,LOWER_UP`, firmware still `version_string=5.82`.

### Previous wrong claims (corrected)

**Previously claimed "bcmdhd.ko is byte-identical across all firmware versions (md5 `8b75e5cd…`)".** This was wrong in context — while true about the *package* versions, the comparison baseline we used (`s50-fs/`) turned out to have been captured post-5.82-upgrade, so we were comparing the Oct 2025 driver against itself. The genuine factory driver is `4cfbf203…`. Corrected after extracting directly from `baseline-2.42/seestarOS.img`.

**Previously speculated "subtle silicon variation" or "OTP-level chip state change" as root cause.** Refuted: simply swapping the driver binary fixes the wedge, proving it's software, not silicon.

### Known unknown [?]

Why some S50 users don't hit this wedge despite receiving the same
Oct 2025 driver is still open. Confirmed facts:
- **[V]** APKs v2.6.4 through v3.1.2 all bundle the Oct 2025 driver (md5 `8b75e5cd…`) as `assets/iscope`
- **[V]** APKs don't download iscope from network at runtime — bundled only
- **[V]** api.seestar.com endpoints hit by the APK are only `/v1/activation` (license) and `/v1/audio-package/audio/version` (sound files), NOT firmware
- **[V]** No firmware package from fw_2.2.0 through fw_3.1.2 updates S50 kernel, DTB, bootloader, or recovery partitions (only S30/S30P models do via `update_img` + `updateEngine`)
- **[V, 2026-04-23]** The DTB property `cap-mmc-hw-reset` is absent on every S50 we have data for, working or broken. So the DTB cannot be the differentiator — ruling out the earlier "production image has a different DTB" hypothesis.
- **[?]** Remaining candidates: chip stepping / silicon revision, per-PCB SDIO timing (e.g., drive strength, pull values), or a boot-time race that only manifests on some boards. None confirmed. A third working unit agreeing to run `./tools/wifi-driver-check.sh` and share `boardrev` + silicon id would narrow this quickly.

---

## Firmware version map

| Package  | `version_int` | App ver  | Status on our S50 | Verification |
|----------|---------------|----------|-------------------|--------------|
| fw_2.6.1 | 2550 | **5.50** | ✅ Works (factory Jul 2023 driver stays installed; fw_2.6.1 doesn't ship bcmdhd.ko) | [V] multiple boots this session |
| fw_2.6.4 | 2582 | 5.82     | ❌ Wedges with stock Oct 2025 driver; ✅ Works with factory Jul 2023 driver swapped in | [V] both outcomes directly observed |
| fw_2.7.0 | 2597 | 5.97     | ❌ Wedges with stock driver | [V] confirmed same HT Avail pattern |
| fw_3.0.0 | 2645 | 6.45     | ❌ Expected to wedge (ships same Oct 2025 driver) | [I] not directly tested |
| fw_3.0.2 | 2670 | 6.70     | ❌ Expected to wedge | [I] not tested |
| fw_3.1.0 | 2706 | 7.06     | ❌ Expected to wedge | [I] not tested |
| fw_3.1.2 | 2732 | 7.32     | ❌ Wedges with stock driver | [V] confirmed when accidentally pushed as mislabeled `iscope` |

---

## Wedge signature

**[V]** On a wedged 5.82+ device with the Oct 2025 driver:

```
[dhd] F1 signature OK, chip:0x4345 rev:0x9 pkg:0x2
[dhd] dhdsdio_write_vars: Download, Upload and compare of NVRAM succeeded.
[dhd] dhdsdio_htclk: HT Avail timeout (1000000): clkctl 0x50
[dhd] dhd_bus_init: clock state is wrong. state = 1
[dhd] ANDROID-ERROR) failed to power up wifi chip, max retry reached
```

`clkctl=0x50` means chip returns `ALP_AVAIL (0x40) | HT_AVAIL_REQ (0x10)` — chip has ALP clock, driver has requested HT, but chip never sets `HT_AVAIL (0x80)`. HT PLL never locks.

**[V]** On working 5.50 with factory driver, some HT Avail timeouts appear on initial retries too, but by retry 3 the chip eventually locks HT and proceeds normally. With the factory driver on 5.82, ZERO HT Avail timeouts occur — cleaner than 5.50.

---

## Hypotheses tested and refuted

All tested because before we found the driver binary difference, we couldn't see a smoking gun in user-visible files.

### A. Chip country priming — REFUTED

**Theory:** priming chip to US via `wl country US` on 5.50 before upgrade would let 5.82's hostapd find a matching regdom.

**[V] Result:** FAILED. Chip confirmed on US on 5.50, pushed 5.82, chip still wedged identically.

### B. systemd `wpa_supplicant.service` mask — REFUTED

**Theory:** new ZWO wpa_supplicant rejects systemd's `-u -s -O` args and restart-loops.

**[V] Result:** FAILED. Masking service on 5.82 device before boot; chip still wedged.

### D. Mount MCU flash skipped — REFUTED

**Theory:** power transient during `AM_Test` flashing `Seestar_2.1.3.bin` wedged the WiFi chip.

**[V] Result:** FAILED. Built custom iscope without the `.bin`, update_package.sh's mount-flash gate failed cleanly and mount flash skipped, chip still wedged.

### E. NVRAM `ccode=DE` removed — REFUTED

**Theory:** donor image's non-standard `ccode=DE` + `regrev=0` appended to `nvram_ap6256.txt` caused the chip to firmware-boot with wrong regulatory state.

**[V] Result:** FAILED. Removed lines (confirmed file shrunk from 2874 → 2854 bytes and driver loaded modified NVRAM). Rebooted 5.82. 60 HT Avail timeouts, still wedged.

### F. Services that trigger wlan0 open during boot — REFUTED as ordering cause

**Theory:** some userspace service opens wlan0 at bad timing and triggers bcmdhd to fail.

**[V] Result:** FAILED. Masked `wpa_supplicant.service + dhcpcd.service + raspberrypi-net-mods.service` all at once. First chip-init moved from 05:12:01 to 05:12:18 (17 seconds later), but chip still wedged identically.

### Independent analysis (bguthro/seestar-api-research)

**[V]** bguthro documents a **separate, transient-only failure mode** where `reload_country` drops `uap0`'s 10.0.0.1 IP during hostapd restart, zwoair_guider's health check fires in the gap, plays sound 33 once, then dhcpcd re-applies the IP and the device stabilizes. His analysis correctly identifies userspace bugs (chmod, ownership).

**[V]** Our failure is a different mode: HT Avail timeout at kernel driver `dhd_bus_init`, wlan0 never comes up at all, persists across every reboot including true cold power cycle. bguthro's fix (re-apply uap0 IP after hostapd restart) wouldn't help our mode.

---

## Confirmed changes 5.50 → 5.82 (file-level, S50)

**[V]** Via `diff` of extracted deb + others/ contents:

| File | 5.50 state | 5.82+ state |
|------|-----------|-------------|
| `/sbin/hostapd` | Debian stock v2.8 | ZWO v2.8.20250701.ACS (md5 `a60c1bdd…`) |
| `/sbin/wpa_supplicant` | Debian stock v2.8 | ZWO v2.8.20250701 (md5 `39419db2…`) |
| `/etc/dhcpcd.conf` | Debian default | ZWO custom (adds `interface uap0 static ip_address=10.0.0.1/24`) |
| `/etc/init.d/dnsmasq` | Debian default | ZWO replacement |
| `/usr/bin/zwo_deleteStarsTool` | not present | new binary |
| `/lib/modules/.../bcmdhd.ko` | Factory Jul 2023 (md5 `4cfbf203…`) | **Oct 2025 rebuild (md5 `8b75e5cd…`) ← this is the regression** |
| `asiair.sh` | no `wl country` block | adds `wl country $set_ccode` at boot |
| `zwoair_daemon.sh` | no chmod +x block | adds chmod +x on new hostapd/wpa_supplicant/dnsmasq |
| `network.sh` | no `reload_country` | adds `reload_country()`, `country`, `get_country` subcommands |
| `zwoair_imager` | no `set_wifi_country` RPC | adds `set_wifi_country` RPC + popen to `network.sh country %s` |

**[V]** Genuinely unchanged:
- `/vendor/etc/firmware/fw_bcm43456c5_ag.bin` — chip firmware blob, md5 `67b79823…` on both
- `/vendor/etc/firmware/nvram_ap6256.txt` — md5 `b7772771…` on both
- Kernel (no `update_img` ever fires on S50)
- DTB (in FIT image at p3, never touched by any update)

**[V]** `update_package.sh` for S50 does NOT flash any partition other than rootfs. For S30/S30P it uses `updateEngine --partition=0x080000|0x280000`; for S50 the code explicitly takes the `else` branch that says `'not update img'`.

---

## Collateral bugs found in 5.82+ (real bugs, not root cause)

These all exist and contribute to a rough upgrade experience but do NOT cause the HT Avail wedge we observed:

1. **[V]** `update_package.sh` leaves `/sbin/hostapd` and `/sbin/wpa_supplicant` owned by `pi` (not `root`) due to `sudo mv` from pi-owned extract dir
2. **[V]** `zwoair_daemon.sh` on 5.82 gates `chmod +x` behind an unrelated `/etc` ownership check, so chmod effectively never fires on normal devices
3. **[V]** `hostapd.service` ExecStart has a cosmetic double `-B` (from `-B -P /run/hostapd.pid -B $DAEMON_OPTS`)
4. **[V]** `update_package.sh` doesn't run `systemctl disable wpa_supplicant.service`, so systemd keeps invoking the new ZWO binary with `-u -s -O` args it rejects — restart-loops forever
5. **[V]** `network.sh:225` has `sudo systemctl restart wpa_supplicant.service` which actively re-invokes the broken systemd-managed path
6. **[V]** 5.97 fixes bug 2 (chmod is now unconditional); no upstream fix yet for 1, 3, 4, 5

---

## THE FIX (confirmed working)

### When WiFi is working on 5.50 (stay there)

Just use it. 5.50 has the factory Jul 2023 driver, no wedge.

### When chip is wedged on 5.82+

1. Don't bother with firmware re-push — the chip state survives iscope swaps
2. `rkdeveloptool` reflash `baseline-2.42/seestarOS.img` (restores factory Jul 2023 driver)
3. Push fw_2.6.1 / 5.50 iscope on top (doesn't ship bcmdhd.ko, so factory driver stays)
4. Run `tools/seestar-recovery.sh --apply` for license, en_eth, etc.

### To run 5.82 (or any later version) WITH working WiFi

**Option 1 (tested):** Push the target firmware, then manually swap in the factory driver:
```bash
./tools/swap_bcmdhd_to_factory.sh
```
Works per verified test.

**Option 2 (not yet built):** Build a custom iscope that substitutes the factory Jul 2023 driver into the package before signing. One-line update to `build_patched_iscope.sh` — swap `others/bcmdhd.ko` after extracting the package, before re-tarring.

---

## USB-C ethernet access

**[V]** `/home/pi/en_eth` marker file toggles USB gadget mode:
- Present → `zwoair_imager`'s popen loop loads `g_ether`, assigns `169.254.100.100/24` to `usb0`
- Absent → USB stays as default `g_mass_storage`

**[V]** `baseline-2.42/seestarOS.img` does NOT ship `/home/pi/en_eth`. Must re-create after any rkdeveloptool reflash. `tools/seestar-recovery.sh` does this automatically via `do_en_eth`.

**[V]** Desktop-side: `tools/desktop-setup/99-seestar-usb.rules` + `seestar-usb-up` auto-configures USB gadget VID:PID `0525:a4a2` to `169.254.100.51/16`.

---

## Tools inventory

All scripts live in `tools/`. Recent additions:

| Tool | Purpose | Status |
|------|---------|--------|
| `extract_factory_bcmdhd.sh` | Loop-mount baseline-2.42, extract factory bcmdhd.ko | [V] works |
| `audit_bcmdhd_across_versions.sh` | MD5+compile-date every bcmdhd.ko in repo + factory | [V] works |
| `swap_bcmdhd_to_factory.sh` | Push factory driver onto running device, backup current, reboot | [V] works |
| `flash_5.50_from_2.42.sh` | Full automation: 2.42 → 5.50 after rkdeveloptool reflash | [V] works |
| `test_bcmdhd_warmup.sh` | Warm `rmmod`/`modprobe` cycle on running device | [V] works (but useful only on working chips) |
| `seestar_firmware_flash.py` | Push signed `iscope` via JSON-RPC | [V] works |
| `sign_firmware.py` | SHA-1 + RSA PKCS1v15 sign tar.bz2 as `iscope` | [V] works |
| `seestar-recovery.sh` | Pre/post upgrade setup (license, wifi, en_eth) | [V] works |
| `verify_stock_5.50.sh` | Compare on-device files to fw_2.6.1 deb | [V] works |
| `install_license_rpc.py` | Install license via `pi_encrypt` JSON-RPC | [V] works |
| `dhdutil/dhdutil` | Cross-compiled (armhf) nexmon dhdutil | [V] builds; ioctls incompat with this driver version |

---

## Hard-won operational rules

1. **[V] DO NOT** push any 5.82+ firmware without either (a) swapping factory driver after, or (b) accepting ~75-min rkdeveloptool recovery
2. **[V] DO NOT** 3-second reset button after failed upgrade — wipes `wpa_supplicant.conf`
3. **[V] DO NOT** pre-add `autochannel_enabled=` to factory 2.42 AP confs — old hostapd rejects → AP never comes up
4. **[V] DO NOT** trust file-level md5 comparisons against `s50-fs/` as a "baseline" — that snapshot is post-upgrade-contaminated; compare against `baseline-2.42/seestarOS.img` contents instead
5. **[V] DO** re-create `/home/pi/en_eth` after any rkdeveloptool reflash
6. **[V] DO** keep USB-C cable + udev rule installed — only non-WiFi SSH path when AP breaks

---

## Open questions

1. **[?]** Most likely explanation for why normal users aren't wedged: **their chips have properly-programmed OTP fuses / SPROM that our prototype donor unit didn't get.** The BCM43456 firmware blob (uploaded each boot) reads per-device calibration and PLL trim values from chip OTP. If the Oct 2025 driver expects certain OTP values that are only programmed during normal factory manufacturing, a prototype chip (boardrev P304, "P" = prototype) might have incomplete OTP → HT PLL refuses to lock. The factory Jul 2023 driver may tolerate unprogrammed/partial OTP where the Oct 2025 rebuild doesn't. This matches the reported ZWO-support workflow: "upload firmware via Broadcom flash utility, then delete the firmware" = reprogram OTP/SPROM via a Broadcom tool that bypasses bcmdhd's normal path, then remove the local override file.

2. **[?]** What specifically in the Oct 2025 bcmdhd.ko rebuild regresses? Would need to diff-compile source revisions (not publicly available) or disassemble and diff .ko → .ko, which is a large project for a small payoff given we have a working fix.

3. **[?]** Does the APK's runtime upgrade path actually push the bundled `asset://iscope`, or fetch something different we haven't traced? Decompiled `DeviceFwFragment.java` sends `"asset://iscope"` to the file socket (port 4361). We haven't MITM'd the bytes on the wire during an APK-driven upgrade — could verify with a proxy but the bundled-asset inference is strong.

4. **[?]** OTP dump of our working 5.50 chip (via `wl otp_dump` or similar) would let us see what fuses ARE set, and comparing against a known-good production unit would confirm or refute the OTP hypothesis. We have no access to a production-unit OTP dump.
