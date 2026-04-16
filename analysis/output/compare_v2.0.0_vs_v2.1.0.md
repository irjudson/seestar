# Seestar v2.0.0 → v2.1.0 Comparison

## Version Mapping Changes

| Field | v2.0.0 | v2.1.0 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `2.95` | `3.31` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.0.0: **77** commands
- Total v2.1.0: **77** commands
- Added: **0**, Removed: **0**, Changed params: **2**

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `stack_after_goto`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `always_make_dark` |
| `get_stack_setting` | `save_discrete_frame`, `save_discrete_ok_frame` | `save_discrete_frame`, `save_discrete_ok_frame`, `cont_capt` |

## API Endpoints

- Total v2.0.0: **79**, v2.1.0: **80**
- Added: **1**, Removed: **0**

### Added Endpoints

- `POST:/v1/app-push/register-token`

## BLE

No changes detected.
