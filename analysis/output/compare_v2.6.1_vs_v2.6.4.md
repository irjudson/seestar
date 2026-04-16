# Seestar v2.6.1 → v2.6.4 Comparison

## Version Mapping Changes

| Field | v2.6.1 | v2.6.4 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `5.50` | `5.82` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.6.1: **80** commands
- Total v2.6.4: **80** commands
- Added: **0**, Removed: **0**, Changed params: **1**

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `rtsp_roi_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `drizzle2x`, `star_trails`, `airplane_line_removal`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `rtsp_roi_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `drizzle2x`, `star_trails`, `airplane_line_removal`, `wide_denoise`, `always_make_dark` |

## API Endpoints

- Total v2.6.1: **97**, v2.6.4: **124**
- Added: **27**, Removed: **0**

### Added Endpoints

- `DELETE:/v1/my-device/{id}`
- `DELETE:/v1/photo-video/tasks/{id}`
- `GET:/common/v1/light-pollution/get`
- `GET:/common/v1/network-available`
- `GET:/v1/ai-assistant/coze-rtc-config`
- `GET:/v1/common/location-bortle`
- `GET:/v1/device-p2p/online-link`
- `GET:/v1/lbs/city-reverse`
- `GET:/v1/my-device`
- `GET:/v1/my-device/detail`
- `GET:/v1/photo-video/tasks`
- `GET:/v1/photo-video/tasks/notification`
- `GET:/v1/photo-video/tasks/quota`
- `GET:/v1/weather/hours24`
- `GET:/v1/weather/now`
- `GET:/v1/weather/sun-moon`
- `GET:/v7/grid-weather/24h`
- `GET:/v7/grid-weather/now`
- `POST:/v1/ai-assistant/quote/rtc-decr`
- `POST:/v1/device-log/report`
- `POST:/v1/device-online/report`
- `POST:/v1/device-p2p/retrieve`
- `POST:/v1/lbs/reverse-geocode`
- `POST:/v1/my-device`
- `POST:/v1/my-device/change-bind`
- `POST:/v1/my-remote-location`
- `POST:/v1/photo-video/tasks`

## BLE Changes ⚠️

- Service UUID: `850e1704-6ecf-49f1-a13f-f5c2d9174f9f` → `850e1701-6ecf-49f1-a13f-f5c2d9174f9f`
- MTU: `500` → `515`
