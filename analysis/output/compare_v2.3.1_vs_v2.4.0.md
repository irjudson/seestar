# Seestar v2.3.1 → v2.4.0 Comparison

## Version Mapping Changes

| Field | v2.3.1 | v2.4.0 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `4.02` | `4.27` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.3.1: **77** commands
- Total v2.4.0: **78** commands
- Added: **1**, Removed: **0**, Changed params: **1**

### Added Commands

| Method | Params |
|--------|--------|
| `get_solve_result` | — |

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `always_make_dark` |

## API Endpoints

- Total v2.3.1: **89**, v2.4.0: **95**
- Added: **6**, Removed: **0**

### Added Endpoints

- `GET:/v1/community/tutorial/index-tops`
- `GET:/v1/lbs/around`
- `GET:/v1/lbs/auto-complete`
- `GET:/v1/lbs/reverse-geocode`
- `GET:/v1/lbs/search`
- `POST:/v1/sync/stargazing-spot`

## BLE

No changes detected.
