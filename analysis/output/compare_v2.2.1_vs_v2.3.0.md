# Seestar v2.2.1 → v2.3.0 Comparison

## Version Mapping Changes

| Field | v2.2.1 | v2.3.0 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `7.32` | `4.00` |
| Target firmware (64-bit) ⚠️ | `7.32` | `—` |
| Pushes device to ⚠️ | `7.32` | `—` |
| Force upgrade below ⚠️ | `26.26` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.2.1: **78** commands
- Total v2.3.0: **77** commands
- Added: **2**, Removed: **3**, Changed params: **1**

### Added Commands

| Method | Params |
|--------|--------|
| `get_annotate_result` | — |
| `set_user_location` | — |

### Removed Commands

| Method |
|--------|
| `get_solve_result` |
| `pause_polar_align` |
| `save_image` |

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `rtsp_roi_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `drizzle2x`, `star_trails`, `airplane_line_removal`, `wide_denoise`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `always_make_dark` |

## API Endpoints

- Total v2.2.1: **124**, v2.3.0: **89**
- Added: **1**, Removed: **36**

### Added Endpoints

- `GET:/api/v1/comets/file`

### Removed Endpoints

- `DELETE:/v1/photo-video/tasks/{id}`
- `GET:/common/v1/light-pollution/get`
- `GET:/common/v1/network-available`
- `GET:/issue-category/list`
- `GET:/v1/ai-assistant/coze-rtc-config`
- `GET:/v1/ai-assistant/quote`
- `GET:/v1/ai-assistant/tts-token`
- `GET:/v1/apass/nearby`
- `GET:/v1/common/location-bortle`
- `GET:/v1/community/tutorial/index-tops`
- `GET:/v1/device-p2p/online-link`
- `GET:/v1/lbs/around`
- `GET:/v1/lbs/auto-complete`
- `GET:/v1/lbs/city-reverse`
- `GET:/v1/lbs/reverse-geocode`
- `GET:/v1/lbs/search`
- `GET:/v1/my-device`
- `GET:/v1/my-device/check-share`
- `GET:/v1/my-device/detail`
- `GET:/v1/my-device/share`
- `GET:/v1/photo-video/tasks`
- `GET:/v1/photo-video/tasks/notification`
- `GET:/v1/photo-video/tasks/quota`
- `GET:/v1/weather/hours24`
- `GET:/v1/weather/now`
- `GET:/v1/weather/sun-moon`
- `POST:/v1/ai-assistant/quote/rtc-decr`
- `POST:/v1/device-log/report`
- `POST:/v1/device-online/report`
- `POST:/v1/lbs/reverse-geocode`
- `POST:/v1/my-device`
- `POST:/v1/my-device/change-bind`
- `POST:/v1/my-device/remove-share`
- `POST:/v1/my-device/share`
- `POST:/v1/photo-video/tasks`
- `POST:/v1/sync/stargazing-spot`

## BLE Changes ⚠️

- Service UUID: `850e1701-6ecf-49f1-a13f-f5c2d9174f9f` → `850e1704-6ecf-49f1-a13f-f5c2d9174f9f`
- MTU: `515` → `500`
