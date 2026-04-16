# Seestar v2.4.1 → v2.5.0 Comparison

## Version Mapping Changes

| Field | v2.4.1 | v2.5.0 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `4.43` | `4.70` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.4.1: **78** commands
- Total v2.5.0: **79** commands
- Added: **1**, Removed: **0**, Changed params: **1**

### Added Commands

| Method | Params |
|--------|--------|
| `pause_polar_align` | — |

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `always_make_dark` |

## API Endpoints

- Total v2.4.1: **95**, v2.5.0: **96**
- Added: **1**, Removed: **0**

### Added Endpoints

- `GET:/v1/ai-assistant/quote`

## BLE

No changes detected.
