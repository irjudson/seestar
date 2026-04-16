# Seestar v1.18.0 → v1.19.0 Comparison

## Version Mapping Changes
| Field | v1.18.0 | v1.19.0 |
|-------|--------|--------|
| Target firmware (32-bit) ⚠️ | `2.53` | `2.61` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v1.18.0: **76** commands
- Total v1.19.0: **76** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v1.18.0: **78**, v1.19.0: **78**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v1.19.0 → v1.20.0 Comparison

## Version Mapping Changes
| Field | v1.19.0 | v1.20.0 |
|-------|--------|--------|
| Target firmware (32-bit) ⚠️ | `2.61` | `2.71` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v1.19.0: **76** commands
- Total v1.20.0: **77** commands
- Added: **1**, Removed: **0**, Changed params: **0**

### Added Commands

| Method | Params |
|--------|--------|
| `stop_func` | — |

## API Endpoints

- Total v1.19.0: **78**, v1.20.0: **78**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v1.20.0 → v1.20.2 Comparison

## Version Mapping Changes

| Field | v1.20.0 | v1.20.2 |
|-------|--------|--------|
| Target firmware (32-bit) ⚠️ | `2.71` | `2.76` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v1.20.0: **77** commands
- Total v1.20.2: **77** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v1.20.0: **78**, v1.20.2: **78**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v1.20.2 → v2.0.0 Comparison

## Version Mapping Changes

| Field | v1.20.2 | v2.0.0 |
|-------|--------|-------|
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
# Seestar v2.0.0 → v2.1.0 Comparison

## Version Mapping Changes

| Field | v2.0.0 | v2.1.0 |
|-------|-------|--------|
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
# Seestar v2.1.0 → v2.2.0 Comparison

## Version Mapping Changes

| Field | v2.1.0 | v2.2.0 |
|-------|-------|--------|
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
# Seestar v2.2.0 → v2.2.1 Comparison

## Version Mapping Changes

| Field | v2.2.0 | v2.2.1 |
|-------|-------|--------|
| Target firmware (32-bit) | `7.32` | `7.32` |
| Target firmware (64-bit) | `7.32` | `7.32` |
| Pushes device to | `7.32` | `7.32` |
| Force upgrade below | `26.26` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.2.0: **78** commands
- Total v2.2.1: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v2.2.0: **124**, v2.2.1: **124**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v2.2.1 → v2.3.0 Comparison

## Version Mapping Changes

| Field | v2.2.1 | v2.3.0 |
|-------|-------|--------|
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
# Seestar v2.3.0 → v2.3.1 Comparison

## Version Mapping Changes

| Field | v2.3.0 | v2.3.1 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `4.00` | `4.02` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.3.0: **77** commands
- Total v2.3.1: **77** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v2.3.0: **89**, v2.3.1: **89**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v2.3.1 → v2.4.0 Comparison

## Version Mapping Changes

| Field | v2.3.1 | v2.4.0 |
|-------|-------|--------|
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
# Seestar v2.4.0 → v2.4.1 Comparison

## Version Mapping Changes

| Field | v2.4.0 | v2.4.1 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `4.27` | `4.43` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.4.0: **78** commands
- Total v2.4.1: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v2.4.0: **95**, v2.4.1: **95**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v2.4.1 → v2.5.0 Comparison

## Version Mapping Changes

| Field | v2.4.1 | v2.5.0 |
|-------|-------|--------|
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
# Seestar v2.5.0 → v2.6.0 Comparison

## Version Mapping Changes

| Field | v2.5.0 | v2.6.0 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `4.70` | `5.34` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.5.0: **79** commands
- Total v2.6.0: **80** commands
- Added: **1**, Removed: **0**, Changed params: **1**

### Added Commands

| Method | Params |
|--------|--------|
| `save_image` | — |

### Changed Command Params

| Method | Before | After |
|--------|--------|-------|
| `get_setting` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `always_make_dark` | `planet_correction`, `auto_3ppa_calib`, `stack_masic`, `auto_power_off`, `frame_calib`, `rec_stablzn`, `wide_cam`, `auto_af`, `ae_bri_percent`, `isp_exp_ms`, `stack_after_goto`, `guest_mode`, `dark_mode`, `rec_res_index`, `rtsp_roi_index`, `af_before_stack`, `usb_en_eth`, `scale`, `angle`, `estimated_hours`, `star_map_ratio`, `star_map_angle`, `cont_capt`, `star_correction`, `drizzle2x`, `star_trails`, `airplane_line_removal`, `always_make_dark` |

## API Endpoints

- Total v2.5.0: **96**, v2.6.0: **97**
- Added: **1**, Removed: **0**

### Added Endpoints

- `GET:/v1/ai-assistant/tts-token`

## BLE

No changes detected.
# Seestar v2.6.0 → v2.6.1 Comparison

## Version Mapping Changes

| Field | v2.6.0 | v2.6.1 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `5.34` | `5.50` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.6.0: **80** commands
- Total v2.6.1: **80** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v2.6.0: **97**, v2.6.1: **97**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v2.6.1 → v2.6.4 Comparison

## Version Mapping Changes

| Field | v2.6.1 | v2.6.4 |
|-------|-------|--------|
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
# Seestar v2.6.4 → v2.7.0 Comparison

## Version Mapping Changes

| Field | v2.6.4 | v2.7.0 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `5.82` | `5.97` |
| Target firmware (64-bit) | `—` | `—` |
| Pushes device to | `—` | `—` |
| Force upgrade below | `—` | `—` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v2.6.4: **80** commands
- Total v2.7.0: **80** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v2.6.4: **124**, v2.7.0: **124**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v2.7.0 → v3.0.0 Comparison

## Version Mapping Changes

| Field | v2.7.0 | v3.0.0 |
|-------|-------|--------|
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
# Seestar v3.0.0 → v3.0.1 Comparison

## Version Mapping Changes

| Field | v3.0.0 | v3.0.1 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `6.45` | `6.58` |
| Target firmware (64-bit) ⚠️ | `6.45` | `6.58` |
| Pushes device to ⚠️ | `6.45` | `6.58` |
| Force upgrade below | `26.26` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v3.0.0: **78** commands
- Total v3.0.1: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v3.0.0: **121**, v3.0.1: **120**
- Added: **1**, Removed: **2**

### Added Endpoints

- `GET:/v1/apass/nearby`

### Removed Endpoints

- `GET:/v7/grid-weather/24h`
- `GET:/v7/grid-weather/now`

## BLE

No changes detected.
# Seestar v3.0.1 → v3.0.2 Comparison

## Version Mapping Changes

| Field | v3.0.1 | v3.0.2 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `6.58` | `6.70` |
| Target firmware (64-bit) ⚠️ | `6.58` | `6.70` |
| Pushes device to ⚠️ | `6.58` | `6.70` |
| Force upgrade below | `26.26` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v3.0.1: **78** commands
- Total v3.0.2: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v3.0.1: **120**, v3.0.2: **120**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v3.0.2 → v3.1.0 Comparison

## Version Mapping Changes

| Field | v3.0.2 | v3.1.0 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `6.70` | `7.06` |
| Target firmware (64-bit) ⚠️ | `6.70` | `7.06` |
| Pushes device to ⚠️ | `6.70` | `7.06` |
| Force upgrade below | `26.26` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v3.0.2: **78** commands
- Total v3.1.0: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v3.0.2: **120**, v3.1.0: **124**
- Added: **4**, Removed: **0**

### Added Endpoints

- `GET:/v1/my-device/check-share`
- `GET:/v1/my-device/share`
- `POST:/v1/my-device/remove-share`
- `POST:/v1/my-device/share`

## BLE

No changes detected.
# Seestar v3.1.0 → v3.1.1 Comparison

## Version Mapping Changes

| Field | v3.1.0 | v3.1.1 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `7.06` | `7.18` |
| Target firmware (64-bit) ⚠️ | `7.06` | `7.18` |
| Pushes device to ⚠️ | `7.06` | `7.18` |
| Force upgrade below | `26.26` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v3.1.0: **78** commands
- Total v3.1.1: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v3.1.0: **124**, v3.1.1: **124**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
# Seestar v3.1.1 → v3.1.2 Comparison

## Version Mapping Changes

| Field | v3.1.1 | v3.1.2 |
|-------|-------|--------|
| Target firmware (32-bit) ⚠️ | `7.18` | `7.32` |
| Target firmware (64-bit) ⚠️ | `7.18` | `7.32` |
| Pushes device to ⚠️ | `7.18` | `7.32` |
| Force upgrade below | `26.26` | `26.26` |
| API base URL | `https://api.seestar.com` | `https://api.seestar.com` |
| Update mechanism | `unknown` | `unknown` |

## Socket Commands

- Total v3.1.1: **78** commands
- Total v3.1.2: **78** commands
- Added: **0**, Removed: **0**, Changed params: **0**

## API Endpoints

- Total v3.1.1: **124**, v3.1.2: **124**
- Added: **0**, Removed: **0**

## BLE

No changes detected.
