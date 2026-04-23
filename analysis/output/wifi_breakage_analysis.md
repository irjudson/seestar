> **SUPERSEDED.** This document was written during the 2026-04 investigation when several root-cause hypotheses were still live. The final, confirmed cause and fix are documented in [`SEESTAR_WIFI_WEDGE_FIX.md`](../../SEESTAR_WIFI_WEDGE_FIX.md) and [`UPGRADE_PROCEDURE_VERIFIED.md`](../../UPGRADE_PROCEDURE_VERIFIED.md). Preserved here as a snapshot of the investigation, not a current description of the bug or fix.

# Seestar S50 WiFi Breakage Root Cause Analysis

**Date:** 2026-04-15 (revised x4)
**Analyzed versions:** App 2.3.0 through 3.1.2 (ASIAIR deb 4.00 through 7.32)
**Evidence base:** s50-fs device filesystem extract, extracted firmware packages for all versions

---

## Summary

There are **three separate WiFi failure modes**, with different causes:

1. **"WiFi is abnormal" at deb 5.50**: AP+STA Same Channel Concurrency conflict. Triggered when home WiFi is configured while the AP is running on a hardcoded channel and ACS (Auto Channel Selection) is disabled. Root cause is that `ccode=` is empty in `sh_conf.txt`, which means the country-code flow that enables ACS was never triggered.

2. **No AP broadcast after upgrading to 5.84**: deb 5.84 adds `network.sh auto` inside the `if wpa_svr=1` block at boot, which re-enables all saved networks and calls `wpa_cli reconfigure`. With saved networks in `wpa_supplicant.conf` and `wpa_svr=1`, wpa_supplicant actively tries to connect on boot, triggering the same SCC conflict before hostapd can bind. The AP never comes up. Persistent, not transient — happens on every boot.

3. **Sound 33 from ACS delay at boot (any version with channel=0)**: When `channel=0` (`autochannel_enabled=1`) is set in `AP_5G.conf`, hostapd performs ACS on every restart — scanning takes 5–30 seconds. The imager's WiFi monitor polls AP state during startup; if it runs before ACS completes, AP info is null and sound 33 plays. This is independent of failure mode 1 and 2 — it triggers even with `wpa_svr=0` and `ap_id_inited=true` correctly set. **Fix: keep `channel=36` before and immediately after upgrade. The app sets `channel=0` via `network.sh country US` during Phase 7 WiFi setup.**

The `rfkill0` toggle in `bluetooth.sh` is **not** a cause. On this hardware (RV1126), `rfkill0` controls Bluetooth only (device path: `platform/wireless-bluetooth`). WiFi is `rfkill1`/`rfkill2` (device path: `platform/ffc70000.dwmmc/ieee80211/phy0`).

---

## Hardware Configuration (from s50-fs sysfs)

| rfkill device | sysfs path | Controls |
|--------------|-----------|---------|
| `rfkill0` | `platform/wireless-bluetooth/rfkill/rfkill0` | **Bluetooth only** |
| `rfkill1` | `platform/ffc70000.dwmmc/ieee80211/phy0/rfkill1` | **WiFi (ieee80211)** |
| `rfkill2` | `platform/ffc70000.dwmmc/mmc1:0001:2/rfkill/rfkill2` | WiFi (device-level) |

## Active AP Configuration (from s50-fs `/home/pi/`)

`wlan0.conf` → `AP_5G.conf` (5GHz AP is active):

```
interface=uap0
hw_mode=a          ← 5GHz
channel=36         ← hardcoded, ACS disabled
ssid=SeestarS50
autochannel_enabled=0
```

`wpa_supplicant.conf` has three saved station-mode networks:

```
network={ ssid="Xiaomi168" ... }       ← 2.4GHz, different band from AP
network={ ssid="ZWO-FACTORY-5G" ... }  ← 5GHz, unknown channel
network={ ssid="<your home SSID>" ... } ← user's home network
```

`sh_conf.txt`:
```
wpa_svr=1     ← station mode enabled
ccode=        ← country code EMPTY — ACS never enabled
```

---

## Failure Mode 1: "WiFi is abnormal" at deb 5.50

### What happens

1. User configures home WiFi via app
2. App writes home SSID/PSK to `wpa_supplicant.conf`, sets `wpa_svr=1`
3. wpa_supplicant starts on `wlan0`, scans for home network
4. Home network is on a different channel than AP's hardcoded channel 36 (or different band entirely)
5. Hardware cannot run AP+STA on different channels (no Same Channel Concurrency)
6. AP fails → imager reports `pi_get_AP wifiName fail` → app displays "WiFi is abnormal"

### Root cause

Country code was never set (`ccode=` empty). The designed path for enabling home WiFi is:

```
app sends country code → network.sh country <ccode>
→ reload_country() enables ACS (autochannel_enabled=1)
→ hostapd restarts with ACS enabled
→ AP picks same channel as connected STA network
→ Same Channel Concurrency works
```

Without a country code, ACS stays disabled and the AP stays hardcoded to channel 36. Any home network on a different channel triggers the conflict.

This is documented in `network.sh` (`reload_country()` function, line 589):
```bash
#必须disable WPA,否则AP来自STA不支持的Same Channel concurrency会导致AP起不来
# Must disable WPA, otherwise AP from STA not supporting Same Channel
# concurrency will cause AP not to start
```
ZWO's own code explicitly stops wpa_supplicant before restarting hostapd for this reason.

### Why the AP survives at 5.50

At deb 5.50 (`fw_2.6.1`), `network.sh auto` is **completely absent** from `asiair.sh` — not present at all, not even inside the `wpa_svr=1` block (confirmed by reading `fw_2.6.1/deb-build/asiair_armhf/home/pi/ASIAIR/asiair.sh`). wpa_supplicant starts but makes one attempt to connect; if it fails the system recovers. The "WiFi is abnormal" error is transient.

---

## Failure Mode 2: No AP broadcast after upgrading to deb 5.84

### What changed (confirmed by diff of extracted packages)

`asiair.sh` in 5.84 (`fw_2.6.4`) adds `network.sh auto` **inside the `if wpa_svr=1` block**:

```bash
wpa_run=$(cat $shell_conf | grep -w wpa_svr=1)
if [ ! -z $wpa_run ]; then
    wpa=$(ps -ef | grep -w wpa_supplicant | grep .conf)
    if [ $? -ne 0 ]; then
        sudo wpa_supplicant -iwlan0 $wpa_cmd
    fi
    sudo /home/pi/ASIAIR/bin/network.sh auto &   # ← added in 5.84
fi
```

`network.sh auto` does (lines 337-345):
```bash
enable_all_ssid        # calls wpa_cli enable_network for each saved network
wpa_cli -i wlan0 reconfigure    # forces wpa_supplicant to reload and rescan
```

Note: `enable_all_ssid` and `wpa_cli reconfigure` both require wpa_supplicant to already be
running — they communicate via its control socket. `network.sh auto` cannot start wpa_supplicant.

With `wpa_svr=1` and saved networks in `wpa_supplicant.conf`, this fires on every boot.

Also noted in `network.sh` comments (lines 225-230):
- *"Restarting after kill works, `wpa_cli reconfigure` doesn't work"*
- *"Cannot use `wpa_cli -i wlan0 reconfigure`"*

ZWO's own developers noted `wpa_cli reconfigure` is unreliable yet it remains in `network.sh auto`.

### Boot sequence at 5.84 that kills the AP

1. `asiair.sh` creates `uap0` virtual interface from `wlan0`
2. `systemctl restart hostapd.service` — tries to bring up 5GHz AP on channel 36
3. `wpa_supplicant -iwlan0` starts (because `wpa_svr=1`)
4. `network.sh auto` → `enable_all_ssid` + `wpa_cli reconfigure`
5. wpa_supplicant scans for and attempts to connect to saved networks
6. SCC conflict → hardware forces wlan0 off channel 36 → `uap0` loses its channel → hostapd fails
7. AP never broadcasts — no SSID visible

### Versions affected

`network.sh auto` is present inside the `if wpa_svr=1` block from **5.84 through 7.32** (all
versions we have). The failure only triggers when `wpa_svr=1`. With `wpa_svr=0`, the entire
block is skipped — wpa_supplicant never starts and `network.sh auto` never runs.

**Every version from 5.84+ has this boot-time failure mode** when:
- `wpa_svr=1` (station mode enabled), AND
- `wpa_supplicant.conf` has saved networks, AND
- Those networks are on different channels than the AP

---

## The `wl country $ccode` call (5.84 and 5.93 only)

`asiair.sh` in **5.84 and 5.93 only** unconditionally runs at boot, regardless of `wpa_svr`:

```bash
ccode=$(grep -E "^\s*ccode\s*=" "$shell_conf" | head -n 1 | sed -E "s/^\s*ccode\s*=\s*//")
sudo wl country $ccode
```

With `ccode=` empty in `sh_conf.txt`, `$ccode` expands to nothing → `sudo wl country` with no
argument. **The effect of calling `wl country` with no argument on the Broadcom driver is
unknown** — it may be a no-op, may read the current setting, or may alter driver state. This
call runs before hostapd restarts.

**From fw_3.0.0 (6.45) onwards, this call is completely removed from `asiair.sh`.**

The previous version of this document claimed the empty-arg call was "harmless." That claim
is not proven from code or observation and has been retracted.

---

## What the Correct Home WiFi Setup Flow Looks Like

The `network.sh country` path is designed to handle this properly:

```
network.sh country <ccode>
  → set_key_value sh_conf.txt ccode <ccode>
  → disable_wpa (stop wpa_supplicant)     ← explicitly stops STA before AP change
  → systemctl stop hostapd
  → wl country <ccode>
  → set autochannel_enabled=1 in AP_2.4G.conf and AP_5G.conf
  → systemctl start hostapd (now with ACS)
  → enable_wpa (restart wpa_supplicant if wpa_svr=1)
```

With ACS enabled, hostapd scans for the least-congested channel that matches what wpa_supplicant
is using, enabling Same Channel Concurrency. The `ccode=` in `sh_conf.txt` should be set to the
user's country code (e.g., "US") as part of this flow.

The app appears to not have sent the country code command, leaving `ccode=` empty and ACS
disabled. This is either a bug in the app's WiFi setup flow or a step the user needs to trigger
separately.

---

## Pre-conditions for Safe Upgrade

### Safe upgrade path (recommended)

**Skip 5.84 and 5.93 entirely. Jump directly from the base image (2.42) to fw_3.0.0 (6.45).**

Reasons:
- 5.84 and 5.93 both have the unconditional `wl country $ccode` call with unknown empty-arg behavior
- fw_3.0.0 (6.45) is the first version where that call is completely removed
- `network.sh auto` remains gated by `wpa_svr=1` in all versions including 6.45+, so
  setting `wpa_svr=0` before upgrade remains valid for any version

**Do not upgrade to 7.32** — that version bricked this device previously.

### Before upgrading to any 5.84+ version

Set `wpa_svr=0` in `/home/pi/.ZWO/sh_conf.txt`. This skips the entire wpa_supplicant
startup block in `asiair.sh` (lines 39-48 in fw_2.6.4), which means:
- wpa_supplicant does not start
- `network.sh auto` does not run
- `wpa_cli reconfigure` is never called

After upgrade, configure home WiFi through the app, which calls `network.sh wpa_svr 1` /
`enable_wpa()` to start wpa_supplicant and `network.sh country <ccode>` to enable ACS.

### What wpa_svr=0 does NOT do

- Does not modify `wpa_supplicant.conf` — saved networks remain
- Does not affect the `wl country $ccode` call in 5.84/5.93 — that runs unconditionally
- Does not affect hostapd startup — AP comes up regardless

---

## Recovery Tool

`seestar-recovery.sh` automates pre-upgrade configuration. Run from laptop while connected
to the device AP (`10.0.0.1`) or home network (`--ip <addr>`):

```
./seestar-recovery.sh                    # show current state
./seestar-recovery.sh --pre-upgrade      # set wpa_svr=0, ccode=US, channel=36 (NOT 0),
                                         # your home WiFi only, remove stale configs,
                                         # preserve ASIAIR_general.xml with ap_id_inited=true
./seestar-recovery.sh --apply            # same but wpa_svr=1, channel=0 (after upgrade)
./seestar-recovery.sh --restore          # restore from backup
./seestar-recovery.sh --install-key      # copy SSH key (one-time, uses password)
```

---

## Version Map

| App version | ASIAIR deb | `wl country $ccode` at boot | `network.sh auto` gated by wpa_svr=1 | Safe to upgrade to |
|-------------|-----------|----------------------------|--------------------------------------|--------------------|
| 2.6.1 | 5.50 | No | No (absent entirely) | — base |
| **2.6.4** | **5.84** | **Yes (unconditional)** | **Yes** | Avoid — use 6.45 instead |
| 2.7.0 | 5.93 | Yes (unconditional) | Yes | Avoid |
| **3.0.0** | **6.45** | **No (removed)** | **Yes** | **Recommended target** |
| 3.0.1 | 6.58 | No | Yes | OK |
| 3.0.2 | 6.70 | No | Yes | OK |
| 3.1.0 | 7.06 | No | Yes | OK |
| 3.1.1 | 7.18 | No | Yes | OK |
| 3.1.2 | 7.32 | No | Yes | **Bricked this device — avoid** |

---

## Files of Interest

| File | Purpose |
|------|---------|
| `/home/pi/.ZWO/sh_conf.txt` | `wpa_svr=1/0`, `ccode=` — key flags |
| `/home/pi/wpa_supplicant.conf` | Saved station-mode WiFi networks |
| `/home/pi/AP_2.4G.conf` | 2.4GHz AP config (channel 11, hw_mode=g) |
| `/home/pi/AP_5G.conf` | 5GHz AP config (channel 36, hw_mode=a) |
| `/home/pi/wlan0.conf` | Symlink → active AP config (currently → AP_5G.conf) |
| `/home/pi/ASIAIR/bin/network.sh` | WiFi management; `country` command enables ACS |
| `/home/pi/ASIAIR/asiair.sh` | Boot startup; `network.sh auto` added in 5.84 |
| `/home/pi/ASIAIR/config` | `version_string`, `version_int` — firmware version |
| `/home/pi/.ZWO/ASIAIR_general.xml` | `ap_id_inited` flag (separate issue, see below) |

---

## The `ap_id_inited` Issue — Root Cause of Sound 33 After Upgrade

This is a **separate failure mode** from the SCC issue and is the confirmed cause of en33.wav
("WiFi is abnormal") even when `wpa_svr=0` is set correctly before the upgrade.

### Mechanism (confirmed via binary analysis of zwoair_imager 6.45)

The 6.45 imager checks `setting2/network/ap_id_inited` from `ASIAIR_general.xml` at startup.
When the flag is **missing or not `true`**, the imager runs AP initialization:

1. Calls `network.sh run_5g 1`
2. `run_5g()` in `common.sh` calls `restart_ap()`:
   ```bash
   restart_ap() {
       sudo /etc/init.d/hostapd stop
       sleep 1
       sudo /etc/init.d/hostapd start
   }
   ```
3. While hostapd is stopped (or during ACS scan if `channel=0`), the imager's WiFi monitor
   (internal function at binary offset `0x47e920`) checks AP state → gets null → **plays sound 33**

The `restart_ap()` call is confirmed at binary offset `0x69bcf0` (`sudo /etc/init.d/hostapd stop;sleep 1;sudo /etc/init.d/hostapd start`), called from the AP initialization path.

### Why this fires on 2.42 → 6.45 upgrade

The recovery script's `--pre-upgrade` step previously deleted **all `.xml` files** from `.ZWO/`,
including `ASIAIR_general.xml`. The 2.42 base image's `ASIAIR_general.xml` already uses the
correct `setting2/` schema with `ap_id_inited=true` — deleting it was unnecessary and harmful.

### Fix

**CRITICAL:** The imager runs with `HOME=/root` (inherited from `asiair.sh` which runs as root via the RC system). It reads and writes `/root/.ZWO/ASIAIR_general.xml`, NOT `/home/pi/.ZWO/ASIAIR_general.xml`. Both files must have `ap_id_inited=true`. Previous fixes only wrote the pi copy — the imager never saw them.

Evidence: `/root/.ZWO/ASIAIR_general.xml` on the s50-fs had `ap_id_inited=false` (written Oct 2022 — the imager wrote it while running as root). The pi copy had `ap_id_inited=true` (the original from the 2019 base image, never updated by the imager).

`ASIAIR_general.xml` must exist with `ap_id_inited=true` in **both** locations before the upgrade runs:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<setting2 date="20190214_181215">
    <network date="20190214_181215">
        <ap_id_inited type="8" date="20190214_181215">true</ap_id_inited>
    </network>
</setting2>
```

Written to both `/home/pi/.ZWO/ASIAIR_general.xml` AND `/root/.ZWO/ASIAIR_general.xml`.

`seestar-recovery.sh --pre-upgrade` step 2b now writes both paths. Previous versions only
wrote the pi path — which the imager never reads.

### Note on ACS and sound 33 — this was the remaining cause after ap_id_inited was fixed

After fixing ASIAIR_general.xml preservation, sound 33 still played. Root cause: `--pre-upgrade`
was setting `channel=0` in `AP_5G.conf` as pre-configuration for SCC. With `channel=0`,
hostapd performs ACS (Auto Channel Selection) on restart — scanning takes 5–30 seconds.
The imager's WiFi monitor polls AP state during that window, finds null, and plays sound 33.
This fires independently of the `ap_id_inited` path.

**Fix**: `--pre-upgrade` no longer sets `channel=0`. It keeps `channel=36` (fast startup).
The app sets `channel=0`/ACS via `network.sh country US` during Phase 7 WiFi setup, which
is the designed flow. `--apply` mode (station mode post-upgrade) still sets `channel=0`.
