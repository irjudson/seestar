# Seestar v2.7.0 → v3.0.0 Comparison

## Version Mapping Changes

| Field | v2.7.0 | v3.0.0 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `5.97` | `6.45` |
| Target firmware (64-bit) ⚠️ | `—` | `6.45` |
| Pushes device to ⚠️ | `—` | `6.45` |
| Force upgrade below ⚠️ | `—` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.7.0: **80** commands
- Total v3.0.0: **78** commands
- Added: **0**, Removed: **2**, Changed params: **0**

### Removed Commands

| Method |
|--------|
| `get_annotate_result` |
| `set_user_location` |

## API Endpoints

- Total v2.7.0: **124**, v3.0.0: **121**
- Added: **1**, Removed: **4**

### Added Endpoints

- `GET:/issue-category/list`

### Removed Endpoints

- `DELETE:/v1/my-device/{id}`
- `GET:/api/v1/comets/file`
- `POST:/v1/device-p2p/retrieve`
- `POST:/v1/my-remote-location`

## BLE

No changes detected.
