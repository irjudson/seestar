# Seestar v1.20.2 → v2.0.0 Comparison

## Version Mapping Changes

| Field | v1.20.2 | v2.0.0 |
|-------|————————|———————|
| Target firmware (32-bit) ⚠️ | `2.76` | `2.95` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v1.20.2: **77** commands
- Total v2.0.0: **77** commands
- Added: **0**, Removed: **0**, Changed params: **1**

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `always_make_dark` |

## API Endpoints

- Total v1.20.2: **78**, v2.0.0: **79**
- Added: **1**, Removed: **0**

### Added Endpoints

- `POST:v1/sync/collection-star`

## BLE

No changes detected.
