# Seestar Firmware Evolution Analysis

**Date:** 2026-04-15 (revised)  
**Versions analyzed:** App 2.3.0 through 3.1.2 (ASIAIR deb 4.00 through 7.32)

---

## Version Summary Table

| App | ASIAIR deb | MCU firmware | Scripts | Binaries | Files | Commands | Endpoints |
|-----|-----------|--------------|---------|----------|-------|----------|-----------|
| 2.3.0 | 4.00 | Seestar_1.9.7.bin | 3 | 2 | 38 | 77 | 89 |
| 2.3.1 | 4.02 | Seestar_1.9.7.bin | 3 | 2 | 38 | 77 | 89 |
| 2.4.0 | 4.27 | Seestar_2.0.3.bin | 3 | 2 | 47 | 78 | 95 |
| 2.4.1 | 4.43 | Seestar_2.0.3.bin | 3 | 2 | 47 | 78 | 95 |
| 2.5.0 | 4.70 | Seestar_2.0.4.bin | 4 | 2 | 52 | 79 | 96 |
| 2.6.0 | 5.34 | Seestar_2.1.2.bin | 4 | 2 | 56 | 80 | 97 |
| 2.6.1 | 5.50 | Seestar_2.1.2.bin | 4 | 2 | 56 | 80 | 97 |
| **2.6.4** | 5.84 | Seestar_2.1.3.bin | 19 | **9** | 37 | 80 | **124** |
| 2.7.0 | **5.93** | Seestar_2.1.4.bin | 19 | 9 | 36 | 80 | 124 |
| **3.0.0** | **6.45** | Seestar_2.1.9.bin | 21 | **18** | **172** | 78 | 121 |
| 3.0.1 | 6.58 | Seestar_2.2.1.bin | 21 | 18 | 176 | 78 | 120 |
| 3.0.2 | 6.70 | Seestar_2.2.2.bin | 22 | 18 | 182 | 78 | 120 |
| 3.1.0 | 7.06 | Seestar_2.2.5.bin | 22 | 18 | 192 | 78 | 124 |
| 3.1.1 | 7.18 | Seestar_2.2.5.bin | 22 | 18 | 192 | 78 | 124 |
| 3.1.2 | **7.32** | Seestar_2.2.5.bin | 22 | 18 | 192 | 78 | 124 |

Bold = significant inflection point.

---

## Inflection Points

### v2.3.0–v2.6.1: Incremental Growth (deb 4.00–5.50)

- Firmware package contains a single `.deb` file installed with `dpkg`
- Asset: `assets/iscope_64` (32-bit ARMv7)
- Only 2 named binaries in the deb (the imager + one other)
- Script count grew from 3 → 4 with the addition of polar alignment support (v2.5.0)
- 38–56 files in the package

### v2.6.4: Package Format Restructuring (deb 5.84) ★

The most structurally significant release. Package format switched from:
- **Before**: Single `asiair_armhf.deb` installed via `dpkg`
- **After**: `deb-build/asiair_armhf/` rsync directory tree

This brought:
- Scripts jumped from 4 → 19 (all shell scripts now shipped as files rather than embedded in deb)
- Named binaries jumped from 2 → 9: `AM_Test`, `air_ble`, `beeper`, `exiv2`, `flash_power_led`, `zwoair_file_server`, `zwoair_guider`, `zwoair_imager`, `zwoair_updater`
- `bluetooth.sh` added (BLE device control)
- `zwoair_imager` binary first extractable for analysis: **10.03 MB**
- API endpoints exploded from 97 → 124 (cloud API expansion)
- **Notable**: Alpaca stub debs (`alpaca_libs_armhf.deb`, `alpaca_update_armhf.deb`) first appeared at v2.6.0 but the actual ASCOM implementation didn't ship until v3.0.0

### v2.7.0: The WiFi Flag Inflection (deb 5.93)

- Minimal file changes (one file removed vs 2.6.4)
- `zwoair_imager` updated to check `setting2/network/ap_id_inited` (see wifi_breakage_analysis.md)
- Still has unconditional `sudo wl country $ccode` at boot (same as 5.84) — empty ccode behavior unknown
- **Recommended to skip** — use 6.45 as upgrade target instead

### v3.0.0: Major Feature Expansion (deb 6.45) ★★ ← RECOMMENDED UPGRADE TARGET

The largest single-version package size increase. Key additions:

**ASCOM/Alpaca (60+ files):**
- Full .NET/Blazor web app: `ascom.alpaca`, `SeestarCtrl.dll`, `Camera.dll`, `Telescope.dll`, etc.
- Startup daemons: `Alpaca.sh`, `AlpacaDaemon.sh`
- ASCOM standard device interfaces for Camera, Focuser, Telescope, FilterWheel, Dome, Rotator, etc.

**Panorama/Mosaic processing binaries (7 new in `/oem/zwo/bin/`):**
- `zwo_cp_find` — control point detection
- `zwo_enblend` — image blending
- `zwo_gen_base` — base image generation
- `zwo_linefind` — line detection
- `zwo_modify_pano` — panorama adjustment
- `zwo_optimiser` — optimization pass
- `zwo_remap` — projection remapping

**AI/ML (first RKNN model):**
- `skyseg_int8_rknn2.rknn` — sky segmentation model

**Stitching libraries:**
- `libzwo_cloud.so.0.0`, `libzwo_features.so.0.0`, `libzwo_stitch.so.0.0`

**Supporting data:**
- IQ parameter files for S30P, S30Plus, S50P variants (IMX585/586/662 sensors)
- `pigz` (parallel gzip), `plot-constellations_my`

**WiFi boot fix:**
- `sudo wl country $ccode` call **removed entirely** from `asiair.sh` — no longer runs at boot
- `network.sh auto` remains gated by `wpa_svr=1` (same as 5.84+); set `wpa_svr=0` before upgrading

**Country code migration (breaking change for upgrades):**
- Country code moved from `sh_conf.txt` → `/oem/zwo/firmware/config.txt`
- `/oem/zwo/firmware/` directory does NOT exist on pre-3.0.0 devices
- `sed` operations silently fail if directory missing

**Commands**: Dropped `get_annotate_result` and `set_user_location` (−2 from 80 → 78)

### v3.0.1: AI Expansion (deb 6.58)

- Added `best_starline640_int8_rknn2.rknn` — star detection/linearity model (640px)
- Added `r_a_w_d_n_o_i_se.rknn` — raw image denoise model
- Added `wpa_supplicant` binary (now ships its own supplicant build)
- 3 AI models total

### v3.0.2: Alpaca Updater + systemd (deb 6.70)

- Added `AlpacaUpdate.sh`, `UpdaterProc.dll` — Alpaca can now self-update
- Added `best_starline640_3class_int8_rknn2.rknn` — 3-class star classification
- Added `systemd/system.conf` and `zwo-rc-local.service`
- 4 AI models total

### v3.1.0: AI Maturity (deb 7.06)

- Added `best_unet256_fp16.onnx` — U-Net segmentation (ONNX format, not RKNN — CPU fallback)
- Added `detect_sun_moon_int8_rknn2.rknn` — solar/lunar detection
- Added `dnoise_1.rknn` — secondary denoise model
- Added system SSH binaries: `sshd-auth`, `sshd-session` (owns SSH stack now)
- Ships `/etc/hostname` and `/etc/hosts` (device identity management)
- 6 AI models total (stable through 3.1.2)

### v3.1.2: Alpaca Relocation (deb 7.32)

- Alpaca installation path moved from `deb-build/Alpaca/` → `deb-build/etc/zwo/Alpaca/`
- Packaged as `alpaca_update_package.zip` for independent updating
- No new AI models, no new commands
- **This is the version that bricked the test device**

---

## Socket Command Evolution

Commands grew from 77 (v2.3.0) to a peak of 80 (v2.6.0–v2.7.0), then dropped to 78 in v3.0.0+.

### Added per version

| Version | Command added |
|---------|--------------|
| 2.4.0 | `get_solve_result` — plate solve result retrieval |
| 2.5.0 | `pause_polar_align` — polar alignment pause/resume |
| 2.6.0 | `save_image` — manual image save trigger |

### Removed in v3.0.0

| Command | Notes |
|---------|-------|
| `get_annotate_result` | Annotation moved to cloud or deprecated |
| `set_user_location` | Location now set via different mechanism |

The command set has been **stable at 78** from v3.0.0 through v3.1.2 — ZWO stopped adding new socket API surface.

---

## AI Model Inventory (by version)

| Model | Purpose | Added | Format |
|-------|---------|-------|--------|
| `skyseg_int8_rknn2.rknn` | Sky segmentation | v3.0.0 | RKNN (NPU) |
| `best_starline640_int8_rknn2.rknn` | Star detection 640px | v3.0.1 | RKNN (NPU) |
| `r_a_w_d_n_o_i_se.rknn` | Raw image denoise | v3.0.1 | RKNN (NPU) |
| `best_starline640_3class_int8_rknn2.rknn` | 3-class star classification | v3.0.2 | RKNN (NPU) |
| `best_unet256_fp16.onnx` | U-Net segmentation | v3.1.0 | ONNX (CPU) |
| `detect_sun_moon_int8_rknn2.rknn` | Solar/lunar target detection | v3.1.0 | RKNN (NPU) |
| `dnoise_1.rknn` | Secondary denoise | v3.1.0 | RKNN (NPU) |

All RKNN models target the Rockchip RV1126 NPU (int8 quantized). The single ONNX model (`best_unet256_fp16.onnx`) is likely a CPU fallback or used on a different inference path.

---

## Imager Binary Growth

| Version | ASIAIR deb | `zwoair_imager` size |
|---------|-----------|----------------------|
| 2.6.4 | 5.84 | 10.03 MB |
| 2.7.0 | 5.93 | 10.05 MB |
| 3.0.0 | 6.45 | 10.34 MB |
| 3.0.1 | 6.58 | 10.37 MB |
| 3.0.2 | 6.70 | 10.37 MB |
| 3.1.0 | 7.06 | 10.41 MB |
| 3.1.2 | 7.32 | 10.41 MB |

Steady growth of ~380 KB from 5.84 → 7.06, then stable. The imager is statically linked — all feature growth is compiled in.

---

## Package Format History

| Era | Format | Install method |
|-----|--------|---------------|
| 2.3.0–2.6.1 (deb 4.00–5.50) | `asiair_armhf.deb` | `dpkg -i` |
| 2.6.4+ (deb 5.84+) | `deb-build/asiair_armhf/` directory tree | `rsync --delete` |
| 3.0.0+ (deb 6.45+) | `deb-build/` expanded with `sysfiles/` subtree | `rsync --delete` (two trees) |

The shift to rsync eliminated the need for dpkg dependency resolution but meant the device must have a compatible base system already installed — no dependency checking.

---

## Camera Sensor Support

IQ parameter files reveal which sensors/hardware configurations ZWO maintains:

| Sensor | Module variant | Device |
|--------|---------------|--------|
| IMX585 | CMK-OT1234-FV0 | S30P, S50P |
| IMX586 | YT-RV1109-2-V1 | S30P, S30Plus, S50P |
| IMX662 | CMK-OT1234-FV0 | S30Plus |

Your S50 uses the IMX585 sensor (based on s50-fs analysis).

---

## Key Risk Summary for Upgrades

| Upgrade path | Risk | Mitigation |
|-------------|------|-----------|
| Base (2.42) → 5.84 or 5.93 | **SKIP** — `wl country` with empty ccode at boot, unknown effect | Go to 6.45 instead |
| Base (2.42) → 6.45 | `network.sh auto` SCC conflict if `wpa_svr=1` at boot | Set `wpa_svr=0` + `ccode=US` before upgrading (use `seestar-recovery.sh --pre-upgrade`) |
| Any → 6.45+ | Country code lost (`/oem/zwo/firmware/` missing on device) | Pre-create directory + config.txt |
| 5.84/5.93 → 6.45 | Same as above | Same mitigation |
| Any → 7.32 | **Bricked this device** — avoid until root cause known | Stop at 7.18 |

**Recommended upgrade path from base image (2.42):**
1. Run `seestar-recovery.sh --pre-upgrade` (sets `wpa_svr=0`, `ccode=US`, your home WiFi only)
2. Push fw_3.0.0 (deb 6.45) directly via your firmware tool
3. Run `seestar-recovery.sh` to verify state
4. Configure home WiFi through app (restores `wpa_svr=1` via `network.sh wpa_svr 1`)

See `wifi_breakage_analysis.md` for full root cause analysis.

---

## Firmware Upgrade Gating Mechanism

### How the App Controls Upgrades

The Seestar app enforces firmware upgrades through **two independent mechanisms**:

1. **Community API path** (server-driven): upgrade availability and force flags are delivered by the backend. No hardcoded firmware minimums here — the server controls policy.
2. **Device-layer path** (client-hardcoded): when the app connects to a Seestar via TCP port 4700, it compares the device-reported `firmware_ver_int` against constants in `ZConfig.java`. This path is fully client-side and has hardcoded thresholds that differ per APK version.

The **community API path** works as follows:

**Stage 1 — App version check** (`GET /v1/setting/config/app`):

Returns `AppConfigData` with:

| JSON field | Type | Meaning |
|-----------|------|---------|
| `app_version` | String | Target app version the server recommends (e.g. `"3.1.2"`) |
| `is_upgrade` | Boolean | Whether the server considers an upgrade available |
| `bt_min_app_version` | String | Minimum app version for BT-path upgrade (added in APK 3.0.2) |
| `bt_min_firmware32_version` | String | Minimum 32-bit firmware for BT-path upgrade (added in APK 3.0.2) |
| `bt_min_firmware64_version` | String | Minimum 64-bit firmware for BT-path upgrade (added in APK 3.0.2) |

Gate logic (`UpgradeService.enableUpgrade()`):
```java
return it.isUpgrade()
    && !isGoogleApk()
    && compareVersion(currentAppVersion, it.getAppVersion()) < 0;
```
Only proceeds if the server says upgrade is available **and** the installed app is older than the recommended version. The `btMin*` fields are passed through to the client but are **not evaluated in `enableUpgrade()`** — they are advisory metadata for the UI or BT delivery path.

**Stage 2 — Force flag check** (`GET /v1/setting/config/app/version?version={target}`):

Returns `AppVersionData` with:

| Field | Type | Meaning |
|-------|------|---------|
| `version` | String | Target app version |
| `isForce` | Int | `1` = force upgrade dialog (non-dismissible); `0` = optional |
| `platform` | String | `"android"` / `"ios"` |
| `description` | List\<String\> | Changelog shown in dialog |

The `getForceUpgrade()` method returns `isForce == 1`. When true, the upgrade dialog cannot be dismissed (`dismissOnBackPressed = false`, `dismissOnTouchOutside = false`).

### Evolution of Version Fields Across APKs

The `AppConfigData` class grew as ZWO added upgrade-path controls:

| APK version | Constructor args | `btMin*` fields |
|------------|------------------|-----------------|
| 2.7.0 | 9 (no `mallLink`, no `btMin*`) | absent |
| 3.0.0 | 10 (adds `mallLink`, no `btMin*`) | absent |
| 3.0.2 | 13 (adds all three `btMin*`) | `bt_min_app_version`, `bt_min_firmware32_version`, `bt_min_firmware64_version` |
| 3.1.2 | 13 (identical to 3.0.2) | same as 3.0.2 |

The `btMin*` fields were introduced at exactly the same release (3.0.2) that added Bluetooth-based firmware delivery infrastructure. Their actual values are server-controlled and not recoverable from the APK alone.

### Device-Side Version Tracking

The device tracks its own version in `/home/pi/ASIAIR/config`:

```bash
version_int=2645       # integer encoding: 2645 = deb 6.45
version_string=6.45    # human-readable string shown in app
version_remark=iscope-2.8  # internal release tag
```

The app reads `version_string` and displays it as "Firmware Version". The `version_int` encoding is `2000 + major*100 + minor` (equivalently: prepend "2" to the version digits with decimal removed), e.g. `6.45 → 2645`, `7.32 → 2732`.

Known `version_int` values from extracted sources:

| ASIAIR deb | `version_int` | `version_remark` | APK |
|-----------|--------------|-----------------|-----|
| 6.45 | 2645 | `iscope-2.8` | 3.0.0 (s50-fs extract) |
| 6.70 | 2670 | `iscope-3.0.2` | 3.0.2 |
| 7.32 | 2732 | `seestar-3.1` | 3.1.2 |

### Functional Minimum Versions (Upgrade Safety)

Even though the app enforces no hardcoded floors, the firmware changes themselves create de-facto minimum requirements:

| Upgrading to | Minimum safe source version | Breaking change |
|-------------|---------------------------|-----------------|
| deb 5.93+ (APK 2.7.0+) | Any | WiFi breaks if `ASIAIR_general.xml` not pre-patched (new `ap_id_inited` key path) |
| deb 6.45+ (APK 3.0.0+) | Any | Country code silently lost if `/oem/zwo/firmware/` doesn't exist on device |
| deb 6.45+ (APK 3.0.0+) | Any | 172 new files, ASCOM/Alpaca stack; rsync install requires clean base |
| deb 7.32+ (APK 3.1.2+) | Any (rsync handles it) | Alpaca installation path moved from `deb-build/Alpaca/` → `deb-build/etc/zwo/Alpaca/`; old path left behind by 3.0.x installs will conflict |

The 3.0.0 jump is the highest-risk upgrade: the `update_package.sh` performs `rsync --delete` over two directory trees (`deb-build/` and `sysfiles/`) and will delete files not in the new package, which can break the system if the device is not already running a compatible base image.

### Device-Layer Version Enforcement (ZConfig.java)

Independent of the community API, the app hardcodes firmware version thresholds in `com.zwo.seestarlib.ZConfig`. These are evaluated every time the app connects to a device (TCP port 4700), by comparing the device-reported `firmware_ver_int` against these constants.

**ZConfig constants per APK version** (extracted from source):

| APK | `firmwareVersion` | `firmwareVersionName` | `firmwareVersion64` | `firmwareAuthenticationChange` | `firmwareWifiChange` |
|-----|------------------|-----------------------|--------------------|---------------------------------|---------------------|
| 2.7.0 | 2597 | "5.97" | *(absent)* | *(absent)* | 2203 |
| 3.0.0 | 2645 | "6.45" | 2645 | **2626** | 2203 |
| 3.0.2 | 2670 | "6.70" | 2670 | 2626 | 2203 |
| 3.1.2 | 2732 | "7.32" | 2732 | 2626 | 2203 |

**Enforcement logic** (`DeviceStateData.java`, both v3.0.0 and v3.1.2):

```java
// Optional upgrade prompt (dismissible)
public boolean getNeedFwUpgrade() {
    return isMaster() && getFwVersion() < getAppFwVersion();  // < firmwareVersion
}

// Forced upgrade prompt (non-dismissible — back button disabled, touch-outside disabled)
public boolean getNeedForceFwUpgrade() {
    return isMaster() && getFwVersion() < 2626;  // hardcoded across all post-3.0.0 APKs
}

// Returns the current APK's target version for upgrade UI display
public int getFwNeedUpdateVersion() {
    checkFwIsX64();
    return 2732;  // matches ZConfig.firmwareVersion for that APK
}
```

**UI caller** (`HomePopupViewHelper.java`, v3.1.2 lines 137, 169):

```java
// Triggered on connect if getNeedFwUpgrade() == true
if (getNeedFwUpgrade()) {
    if (getNeedForceFwUpgrade()) {
        // showSingleConfirm() — only OK button, cannot cancel
    } else {
        // showConfirm() — OK + Cancel
    }
}
```

**What each threshold means in practice:**

| Constant | Value | deb version | Effect |
|----------|-------|-------------|--------|
| `firmwareAuthenticationChange` | 2626 | 6.26 | **Hard floor**: any device with deb < 6.26 connected to APK 3.0.0+ receives a non-dismissible forced upgrade dialog. Introduced at APK 3.0.0, unchanged through 3.1.2. |
| `firmwareVersion` / `firmwareVersion64` | varies | per-APK | **Soft floor**: device with deb < current target receives optional (dismissible) upgrade prompt. Raised at each major APK release. |
| `firmwareWifiChange` | 2203 | 2.03 | **Feature gate**: WiFi band-switching UI (`ConnectDialog.getEnableWifiChange()`) hidden unless device firmware ≥ 2.03. Effectively all modern devices pass this. |

**Key implication**: The `firmwareAuthenticationChange = 2626` threshold was introduced with APK 3.0.0 and has **never been raised**. This means every APK from 3.0.0 onward will force-upgrade any device running deb < 6.26. Devices running the current user's firmware (deb 6.45, `version_int = 2645`) are above this floor and receive only the optional prompt (unless the server delivers `isForce = 1`).

### API Endpoints for Upgrade Flow

```
GET /v1/setting/config/app          → AppConfigData  (is_upgrade, app_version, btMin* fields)
GET /v1/setting/config/app/version  → AppVersionData (isForce, description, platform)
```

Both are on the community API base URL (not the device's local TCP port 4700).
