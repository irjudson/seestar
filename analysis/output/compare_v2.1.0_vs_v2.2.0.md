# Seestar v2.1.0 → v2.2.0 Comparison

## Version Mapping Changes

| Field | v2.1.0 | v2.2.0 |
|-------|———————|———————|
| Target firmware (32-bit) ⚠️ | `3.31` | `7.32` |
| Target firmware (64-bit) ⚠️ | `—` | `7.32` |
| Pushes device to ⚠️ | `—` | `7.32` |
| Force upgrade below ⚠️ | `—` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.1.0: **77** commands
- Total v2.2.0: **78** commands
- Added: **3**, Removed: **2**, Changed params: **2**

### Added Commands

| Method | Params |
|--------|--------|
| `get_solve_result` | — |
| `pause_polar_align` | — |
| `save_image` | — |

### Removed Commands

| Method |
|--------|
| `get_annotate_result` |
| `set_user_location` |

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `stack_after_goto`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `rtsp_roi_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `drizzle2x`, `star_trails`, `airplane_line_removal`, `wide_denoise`, `always_make_dark` |
| `get_stack_setting` | `save_discrete_frame`, `save_discrete_ok_frame`, `cont_capt` | `save_discrete_frame`, `save_discrete_ok_frame` |

## API Endpoints

- Total v2.1.0: **80**, v2.2.0: **124**
- Added: **45**, Removed: **1**

### Added Endpoints

- `DELETE:/v1/photo-video/tasks/{id}`
- `GET:/comment-feedback/list`
- `GET:/comment-feedback/unread`
- `GET:/common/v1/light-pollution/get`
- `GET:/common/v1/network-available`
- `GET:/issue-category/list`
- `GET:/issue-notification`
- `GET:/opercenter/v2/advertises`
- `GET:/v1/ai-assistant/coze-rtc-config`
- `GET:/v1/ai-assistant/quote`
- `GET:/v1/ai-assistant/tts-token`
- `GET:/v1/apass/nearby`
- `GET:/v1/common/location-bortle`
- `GET:/v1/community/tutorial/index-tops`
- `GET:/v1/device-p2p/online-link`
- `GET:/v1/dialog/user/unread`
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
- `GET:/v1/setting/product-mall-links`
- `GET:/v1/weather/hours24`
- `GET:/v1/weather/now`
- `GET:/v1/weather/sun-moon`
- `POST:/opercenter/v2/advertises/{id}/touch`
- `POST:/v1/ai-assistant/quote/rtc-decr`
- `POST:/v1/device-log/report`
- `POST:/v1/device-online/report`
- `POST:/v1/lbs/reverse-geocode`
- `POST:/v1/my-device`
- `POST:/v1/my-device/change-bind`
- `POST:/v1/my-device/remove-share`
- `POST:/v1/my-device/share`
- `POST:/v1/photo-video/tasks`
- `POST:/v1/sync/plans`
- `POST:/v1/sync/stargazing-spot`
- `PUT:/comment-feedback/read`

### Removed Endpoints

- `GET:/api/v1/comets/file`

## BLE Changes ⚠️

- Service UUID: `850e1704-6ecf-49f1-a13f-f5c2d9174f9f` → `850e1701-6ecf-49f1-a13f-f5c2d9174f9f`
- MTU: `500` → `515`
