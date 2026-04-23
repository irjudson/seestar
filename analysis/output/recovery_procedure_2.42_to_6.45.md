> **SUPERSEDED.** This document was written during the 2026-04 investigation when several root-cause hypotheses were still live. The final, confirmed cause and fix are documented in [`SEESTAR_WIFI_WEDGE_FIX.md`](../../SEESTAR_WIFI_WEDGE_FIX.md) and [`UPGRADE_PROCEDURE_VERIFIED.md`](../../UPGRADE_PROCEDURE_VERIFIED.md). Preserved here as a snapshot of the investigation, not a current description of the bug or fix.

# Recovery Procedure: Fresh 2.42 Image → deb 6.45 (fw_3.0.0)

**Date:** 2026-04-15 (revised x2)  
**Device:** Seestar S50, SN 77d82606, cpuId 2c0927865bd10180  
**Starting state:** Fresh seestarOS.img (deb 2.42)  
**Target:** ASIAIR deb 6.45 (fw_3.0.0 / app 3.0.0)  
**Skipping:** deb 5.84 and 5.93 — both have `sudo wl country $ccode` unconditionally at boot
with unknown behavior when ccode is empty. 6.45 removes this call entirely.

---

## What you need

| Item | Location |
|------|----------|
| Recovery script | `Seestar/seestar-recovery.sh` |
| License file | `Seestar/s50-fs/home/pi/.ZWO/zwoair_license` (md5: c414956cdbe8bea4e7c6ba89a0a16328) |
| Firmware tool | your separate firmware push tool |
| fw_3.0.0 package | `Seestar/seestar-analysis/output/_fw_work/fw_3.0.0/` |

---

## Phase 1: Flash base image

Flash `seestarOS.img` via rkdeveloptool. The device will come up with:
- AP SSID: `SeestarS50` (or similar)
- AP password: `12345678` (default) or `HolyCow!`
- SSH password: `raspberry`
- Firmware: deb 2.42, `wpa_svr=0` (confirmed from fresh flash)

Connect your laptop to the device AP. Verify SSH works:
```bash
ssh pi@10.0.0.1   # password: raspberry
```

---

## Phase 2: Install SSH key (one-time)

```bash
./seestar-recovery.sh --install-key
# prompts for password: raspberry
```

After this, no password prompts for subsequent runs.

---

## Phase 3: Check current state

```bash
./seestar-recovery.sh
```

Expected on fresh 2.42 image:
- `firmware version: 2.42`
- `wpa_svr: wpa_svr=0` ← already correct for pre-upgrade
- `ccode: (missing)` ← needs setting to US
- `license md5: WRONG` ← needs replacing
- `channel: channel=36` ← already correct (leave at 36, do NOT set to 0)
- `autochannel_enabled: (missing)` ← leave absent (app sets this in Phase 7)
- `wpa networks: "Xiaomi168" "ZWO-FACTORY-5G"` ← need replacing

---

## Phase 4: Apply pre-upgrade configuration

```bash
./seestar-recovery.sh --pre-upgrade
```

This sets:
- `wpa_svr=0` (already set on fresh 2.42 image, idempotent)
- `ccode=US` — so `wl country US` runs at boot in 5.84/5.93 (not relevant for 6.45 but harmless)
- `channel=36` in AP_5G.conf — **NOT 0** (see below)
- `wlan0.conf → AP_5G.conf` symlink
- wpa_supplicant.conf: your home WiFi only, country=US
- Removes stale xml/json/txt files from .ZWO/ **except ASIAIR_general.xml** (see below)
- Writes `ASIAIR_general.xml` with `ap_id_inited=true`
- Copies correct license file

**Why channel=36 (NOT channel=0) before upgrade:**
Setting `channel=0` (ACS / Auto Channel Selection) causes hostapd to scan for the
least-congested channel on every restart. This scan takes 5–30 seconds, during which the
AP is not broadcasting. The imager starts during boot, polls AP state, finds null, and
plays sound 33 ("WiFi is abnormal") — regardless of whether `ap_id_inited=true` is set.

`channel=0` is only needed for Same Channel Concurrency once home WiFi is configured.
The app's `network.sh country US` call (Phase 7) already sets `channel=0` and
`autochannel_enabled=1` as part of the designed WiFi setup flow. There is no reason to
pre-configure it before the upgrade.

**Why ASIAIR_general.xml must be preserved / written:**
The 6.45 imager checks `setting2/network/ap_id_inited` at startup. If missing, it runs
AP initialization: calls `network.sh run_5g 1` → `restart_ap()` in common.sh →
`sudo /etc/init.d/hostapd stop; sleep 1; sudo /etc/init.d/hostapd start`.
This restart window also triggers sound 33. The base image's `ASIAIR_general.xml`
already has `ap_id_inited=true` in `setting2/` schema — correct for 6.45.
Previous procedure deleted it; that was also a bug (now fixed).

Verify with `./seestar-recovery.sh` — everything should show correct.

---

## Phase 5: Push fw_3.0.0 (deb 6.45)

Use your firmware push tool to push `fw_3.0.0` to the device while connected to the AP.

The `update_package.sh` in that directory performs:
1. `rsync` of `deb-build/asiair_armhf/` to `/` on the device
2. Mount MCU firmware update (`Seestar_2.1.9.bin`)
3. Restart imager/guider daemons
4. Reboot if kernel files changed

Watch LEDs for progress. After reboot, reconnect to `SeestarS50` AP.

---

## Phase 6: Verify post-upgrade state

```bash
./seestar-recovery.sh
```

Expected:
- `firmware version: 6.45`
- `wpa_svr: wpa_svr=0`
- `ccode: ccode=US`
- `license md5: c414956...  [GOOD]`
- `channel: channel=36` ← ACS not yet enabled (app sets it in Phase 7)
- `autochannel_enabled: (missing or 0)`

---

## Phase 7: Configure home WiFi through the app

Connect phone to `SeestarS50` AP and open the Seestar app (APK 3.0.0+). Configure
home WiFi. The app will call `network.sh country US` → `reload_country()`, which:
- Stops wpa_supplicant
- Sets `ccode=US` and `autochannel_enabled=1`
- Restarts hostapd with ACS enabled
- Restarts wpa_supplicant (sets `wpa_svr=1`)

After this, the device will be in station mode with ACS enabled for Same Channel Concurrency.

---

## Phase 8: Verify station mode

```bash
./seestar-recovery.sh --ip 192.168.2.47   # or whatever IP home network assigns
```

Expected:
- `firmware version: 6.45`
- `wpa_svr: wpa_svr=1`
- `wpa networks: "<your home SSID>"`
- Device reachable at home network IP

---

## Key differences from previous procedure (2.42 → 5.93)

| Old procedure | This procedure |
|--------------|----------------|
| Target: deb 5.93 | Target: deb 6.45 |
| Manual SSH commands | `seestar-recovery.sh --pre-upgrade` |
| Required pre-patching ASIAIR_general.xml | Must PRESERVE it with ap_id_inited=true |
| No `ccode` consideration | `ccode=US` set explicitly |
| Set `channel=0`/ACS pre-upgrade | Keep `channel=36` pre-upgrade; app sets ACS in Phase 7 |

---

## Device Identity Reference

| Field | Value |
|-------|-------|
| SN | 77d82606 |
| cpuId | 2c0927865bd10180 |
| auth_code | 591746ca2eb046e99832ed462dbc5b7c |
| AP SSID | SeestarS50 |
| AP password | HolyCow! |
| License md5 | c414956cdbe8bea4e7c6ba89a0a16328 |
| Target deb | 6.45 |
| fw_ directory | fw_3.0.0 |
