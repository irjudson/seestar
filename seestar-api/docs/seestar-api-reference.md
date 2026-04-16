# Seestar Telescope Control API Reference

Reverse-engineered from ZWO Seestar Android app v3.0.2 and the on-device ASCOM Alpaca server.

## Architecture Overview

The Seestar smart telescope runs Linux on an ARM64 SoC (RK3566/RK3568) with an ESP32-S3 mount controller. All communication happens over WiFi (device creates an AP at `192.168.110.1`).

### Protocol Layers

| Layer | Transport | Port(s) | Description |
|-------|-----------|---------|-------------|
| Commands | TCP | 4700 | Line-delimited JSON, main control channel |
| Images (telephoto) | TCP | 4800 | Live preview image stream |
| Images (wide) | TCP | 4804 | Wide-angle camera stream |
| Video (telephoto) | RTMP | 4554 | RTMP video stream |
| Video (wide) | RTMP | 4555 | Wide-angle RTMP stream |
| File Transfer | TCP | 4801 | Image/file download |
| Discovery | UDP | 4720 | Device discovery broadcast |
| Firmware Command | TCP | 4350 | Firmware update control |
| Firmware Upload | TCP | 4361 | Firmware binary upload |
| ASCOM Alpaca | HTTP | 80 | Standard ASCOM REST API |

### Device Models

- **S30** - Seestar S30
- **S50** - Seestar S50
- **S30Pro** - Seestar S30 Pro
- **S30Plus** - Seestar S30 Plus
- **S50Pro** - Seestar S50 Pro

---

## 1. Discovery Protocol (UDP 4720)

### Discover Devices

Broadcast a scan request to the network broadcast address on port 4720:

```json
{"method":"scan_iscope","params":"","id":1}\r\n
```

### Discovery Response

```json
{
  "code": 0,
  "id": 1,
  "jsonrpc": "2.0",
  "method": "scan_iscope",
  "result": {
    "ssid": "Seestar_XXXXXX",
    "sn": "SERIAL_NUMBER",
    "model": "Seestar",
    "bssid": "AA:BB:CC:DD:EE:FF",
    "is_verified": true,
    "product_model": "Seestar S50",
    "tcp_client_num": 1,
    "pwd": "...",
    "serc": "..."
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ssid` | string | Device WiFi SSID |
| `sn` | string | Serial number |
| `model` | string | Model identifier |
| `product_model` | string | Human-readable model name |
| `is_verified` | bool | Whether device is verified |
| `tcp_client_num` | int | Current TCP connections (max 8) |

---

## 2. Connection Protocol (TCP 4700)

### Message Format

All messages are JSON objects terminated with `\r\n` (CRLF). Each request includes a monotonically increasing `id` field that is echoed in the response.

### Handshake

**Step 1 - Get Challenge:**

```json
→ {"id":1,"method":"get_verify_str"}\r\n
← {"code":0,"id":1,"result":{"str":"RANDOM_CHALLENGE"}}\r\n
```

**Step 2 - RSA Verify:**

Encrypt the challenge string using RSA PKCS1v15 with the device's public key, base64-encode the result:

```json
→ {"id":2,"method":"verify_client","params":{"sign":"BASE64_ENCRYPTED","data":"RANDOM_CHALLENGE"}}\r\n
← {"code":0,"id":2}\r\n
```

**RSA Public Key** (base64 DER SubjectPublicKeyInfo):
```
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDRsuHZIML9s8t9wTOOx1Rtpmb
DGKurd1rPsv/OrrhQYQXrpuECRdd2KBHQm5N5Nevy17ryrCMSV1Gp4I+VuiNXqt
ibjO2KRq/AtsjrWCE7J11d3tjmbRB/mCcpRRRXA1JBpL9xhDuYG4VvqdNM9B328
saLD1vnd/TYKsES7kXm2wIDAQAB
```

### Heartbeat

Send every 4 seconds to keep the connection alive:

```json
→ {"method":"test_connection","id":1}\r\n
```

### Standard Response Format

```json
{
  "id": <transaction_id>,
  "method": "<method_name>",
  "code": 0,
  "result": { ... }
}
```

**Error codes:**
- `0` - Success
- `103` - Method not found
- `318` - Partial error (check `error` field)

### Connection State Machine

```
DISCONNECTED → CONNECTING → HANDSHAKE → CONNECTED
                                           ↓ (link lost)
                                        RECONNECTING → CONNECTED
                                           ↓ (3 failures)
                                         FAILED
```

- **Socket timeout:** 2500ms
- **Heartbeat interval:** 4000ms
- **Reconnect delay:** 3000ms
- **Max reconnect attempts:** 3

---

## 3. Command Reference

### 3.1 Mount / Scope

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Get RA/Dec | `scope_get_equ_coord` | — | `{ra: float, dec: float}` |
| Get Alt/Az | `scope_get_horiz_coord` | — | `{alt: float, az: float}` |
| Get State | `scope_get_state` | — | Mount state object |
| Get Tracking | `scope_get_track_state` | — | `bool` |
| Set Tracking | `scope_set_track_state` | `bool` | — |
| Speed Move | `scope_speed_move` | `{angle, percent, level, dur_sec}` | — |
| Abort Slew | `scope_move` | `["none"]` | — |
| Park | `scope_park` | — | — |
| Sync | `scope_sync` | `{ra, dec}` | — |
| Set Location | `scope_set_location` | `{lat, lon, alt}` | — |
| Set Time | `scope_set_time` | `{timestamp}` | — |
| Set EQ Mode | `scope_set_eq_mode` | `{equ_mode: bool}` | — |
| Move to Horizon | `scope_move_to_horizon` | — | — |
| Auto Goto | `start_auto_goto` | `{ra, dec, target_name, mode, lp_filter}` | — |
| Stop Goto | `stop_auto_goto` | — | — |
| Set User Location | `set_user_location` | `{lat, lon}` | — |
| Get User Location | `get_user_location` | — | Location object |
| Get Meridian Setting | `get_merid_setting` | — | Meridian config |
| Set Meridian Setting | `set_merid_setting` | Config params | — |

### 3.2 Camera

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Open | `open_camera` | — | — |
| Close | `close_camera` | — | — |
| Get Info | `get_camera_info` | — | Camera info |
| Get State | `get_camera_state` | — | Camera state |
| Get Control | `get_control_value` | `{type: string}` | Control value |
| Set Control | `set_control_value` | `{type: string, value: any}` | — |
| Start Exposure | `start_exposure` | — | — |
| Stop Exposure | `stop_exposure` | — | — |
| Continuous Expose | `start_continuous_expose` | — | — |
| Get Controls | `get_controls` | — | List of controls |
| Save Image | `save_image` | — | — |
| Save Stack | `save_stack` | — | — |

**Control Types:** `Exposure`, `Gain`, `Offset`, `Red`, `Blue`, `HardwareBin`, `MonoBin`, `CoolerOn`, `CoolPowerPerc`, `TargetTemp`, `Temperature`, `AntiDewHeater`, `FrameSize`, `ISO`, `batterylevel`, `previewzoom`, `zoomposition`

**Camera States:** `idle`, `exposing`, `expose`, `download`, `cooling`, `close`, `error`, `first_delay`, `frame_delay`, `target_delay`, `guide_settling`, `dither_settling`, `meridian_flip`, `change_target`

### 3.3 Focuser

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Open | `open_focuser` | — | — |
| Close | `close_focuser` | — | — |
| Move | `move_focuser` | `{step: int, ret_step: bool}` | `{step: int}` |
| Stop | `stop_focuser` | — | — |
| Auto Focus | `start_auto_focuse` | — | — |
| Stop AF | `stop_auto_focuse` | — | — |
| Get Position | `get_focuser_position` | — | Position |
| Get State | `get_focuser_state` | — | Focuser state |
| Reset Factory | `reset_factory_focal_pos` | — | — |

### 3.4 Filter Wheel

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Open | `open_wheel` | — | — |
| Close | `close_wheel` | — | — |
| Get Position | `get_wheel_position` | — | Position int |
| Set Position | `set_wheel_position` | `{position: int}` | — |
| Get State | `get_wheel_state` | — | Wheel state |
| Calibrate | `calibrate_wheel` | — | — |
| Get Slot Names | `get_wheel_slot_name` | — | List of names |
| Set Slot Names | `set_wheel_slot_name` | `{names: []}` | — |

### 3.5 View / Preview

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Start View | `iscope_start_view` | `{mode, target_name?, target_ra_dec?, lp_filter?}` | — |
| Stop View | `iscope_stop_view` | `{stage?}` | — |
| Cancel View | `iscope_cancel_view` | — | — |
| Get State | `get_view_state` | — | View state |

**View Modes:** `star`, `moon`, `sun`, `scenery`, `planet`

### 3.6 Stacking

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Start Stack | `iscope_start_stack` | `{restart: bool}` | — |
| Start Batch | `start_batch_stack` | — | — |
| Stop Batch | `stop_batch_stack` | — | — |
| Clear Batch | `clear_batch_stack` | — | — |
| Start Planet | `start_planet_stack` | `{file, mode}` | — |
| Stop Planet | `stop_planet_stack` | — | — |
| Clear | `clear_stack` | — | — |
| Is Stacked | `is_stacked` | — | `bool` |
| Get Info | `get_stack_info` | — | Stack info |
| Get Stacked Img | `get_stacked_img` | — | Stacked image |

### 3.7 Plate Solving

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Start | `start_solve` | — | — |
| Stop | `stop_solve` | — | — |
| Get Result | `get_solve_result` | — | `{ra_dec, code, error, state}` |
| Get Last | `get_last_solve_result` | — | Same as above |

### 3.8 Image Management

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| List Files | `get_img_file` | — | File list |
| Get File Info | `get_img_file_info` | `{name}` | File info |
| Get Thumbnail | `get_img_thumbnail` | `{name}` | Thumbnail data |
| Delete | `delete_image` | `{name}` | — |
| Delete All | `delete_all_image` | — | — |
| Get Current | `get_current_img` | — | Current image |
| Annotate | `start_annotate` | — | — |
| AI Process | `start_ai_process` | — | — |
| Get Albums | `get_albums` | — | Album list |

### 3.9 Streaming

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Start Stream | `begin_streaming` | — | — |
| Stop Stream | `stop_streaming` | — | — |
| Start AVI | `start_record_avi` | — | — |
| Stop AVI | `stop_record_avi` | — | — |
| Get RTMP Config | `get_rtmp_config` | — | RTMP config |
| Set RTMP Config | `set_rtmp_config` | Config params | — |

### 3.10 Polar Alignment

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Start | `start_polar_align` | — | — |
| Stop | `stop_polar_align` | — | — |
| Pause | `pause_polar_align` | — | — |
| Clear | `clear_polar_align` | — | — |
| Check Alt | `check_pa_alt` | — | — |
| Get Polar Axis | `get_polar_axis` | — | Polar axis data |
| Get 3PPA Setting | `get_3p_pa_setting` | — | 3PPA config |
| Set 3PPA Setting | `set_3p_pa_setting` | Config params | — |

### 3.11 System

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Get Device State | `get_device_state` | — | Complete state |
| Get App State | `iscope_get_app_state` | — | App state |
| Shutdown | `pi_shutdown` | — | — |
| Reboot | `pi_reboot` | — | — |
| Get Info | `pi_get_info` | — | System info |
| Get/Set Time | `pi_get_time` / `pi_set_time` | `{timestamp}` | — |
| Get/Set AP | `pi_get_ap` / `pi_set_ap` | `{ssid, passwd, is_5g}` | AP info |
| Station Scan | `pi_station_scan` | — | Network list |
| Station Connect | `pi_station_select` | `{ssid, passwd}` | — |
| Station State | `pi_station_state` | — | Station state |
| Get Disk Volume | `get_disk_volume` | — | Storage info |
| Check Internet | `check_internet` | — | `bool` |

### 3.12 Settings

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Get Settings | `get_setting` | — | Full settings object |
| Set Setting | `set_setting` | Key-value pairs | — |

**Key settings:** `expert_mode`, `auto_3ppa_calib`, `auto_power_off`, `stack_after_goto`, `dark_mode`, `guest_mode`, `wide_cam`, `isp_exp_ms`, `stack_lenhance` (LP filter), `mosaic`, `stack_dither`, `beep_volume`, etc.

### 3.13 Planning

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| List Plans | `list_plan` | — | Plan list |
| Get Plan | `get_plan` | `{name}` | Plan data |
| Set Plan | `set_plan` | Plan data | — |
| Delete Plan | `delete_plan` | `{name}` | — |
| Import Plan | `import_plan` | Plan data | — |
| Get Enabled | `get_enabled_plan` | — | Active plan |

### 3.14 Calibration

| Command | Method String | Parameters | Response |
|---------|--------------|------------|----------|
| Compass Cal Start | `start_compass_calibration` | — | — |
| Compass Cal Stop | `stop_compass_calibration` | — | — |
| Compass State | `get_compass_state` | — | Compass state |
| G-Sensor Cal | `start_gsensor_calibration` | — | — |

---

## 4. Event Reference

Events arrive as JSON messages with an `Event` field instead of an `id`/`method` pair:

```json
{"Event":"AutoGoto","state":"working","timestamp":"..."}
```

### Event Categories

| Category | Events |
|----------|--------|
| **APP_STATE** | SelectCamera, View, SecondView, Initialise, DarkLibrary, 3PPA, ContinuousExposure, Stack, AviRecord, ViewPlan, Target, AutoGoto, ScopeGoto, Exposure, PlateSolve, RTSP, ObjectTrack, AutoFocus, FocuserMove, GoPixel, ScanSun, CheckPhotoMetry |
| **DEVICE_STATE** | PiStatus, DiskSpace, Client, Setting, ScopeHome, ScopeMoveToHorizon, MountMode, WheelMove |
| **OTHER** | SaveImage, Alert, Unknown |

### Additional Events (from MainCameraConstants)

BatchStack, PlanetStack, BalanceSensor, CameraStateChange, CoolerPower, CreateCalibFrame, DeviceChange, Dither, ExportImage, FindStar, MeridianFlip, RestartGuide, Sequence, Temperature, Warning, WheelCalibrate, and more.

---

## 5. State Model

The complete device state is returned by `get_device_state`:

```json
{
  "device": { "name", "sn", "product_model", "firmware_ver_int", "firmware_ver_string", "focal_len", "fnumber", "is_verified", ... },
  "mount": { "tracking", "close", "move_type", "equ_mode" },
  "camera": { "chip_size", "debayer_pattern", "focal_len", "pixel_size_um" },
  "second_camera": { ... },
  "focuser": { "step", "max_step", "state" },
  "second_focuser": { ... },
  "ap": { "ssid", "passwd", "is_5g" },
  "station": { "server", "freq", "ip", "ssid", "gateway", "netmask", "sig_lev", "key_mgmt" },
  "pi_status": { "temp", "is_overtemp", "is_undervolt", "charger_status", "battery_capacity", "charge_online", "battery_temp", ... },
  "setting": { ... },
  "client": { ... },
  "storage": { "is_typec_connected", "connected_storage", "storage_volume", "cur_storage" },
  "balance_sensor": { "code", "data" },
  "compass_sensor": { "code", "data" }
}
```

---

## 6. ASCOM Alpaca API

The on-device Alpaca server (v1.2.0-3, .NET 8.0) provides standard ASCOM REST endpoints.

**Base URL:** `http://<device_ip>/api/v1/{device_type}/{device_number}/{property}`

### Available Devices

| Device Type | Description |
|-------------|-------------|
| telescope/0 | Mount control (slew, track, park) |
| camera/0 | Primary camera |
| focuser/0 | Primary focuser |
| filterwheel/0 | Filter wheel |
| rotator/0 | Rotator |
| covercalibrator/0 | Cover/calibrator |
| switch/0 | Switch array |

### Example Requests

```bash
# Get RA
GET /api/v1/telescope/0/rightascension?ClientID=1&ClientTransactionID=1

# Start exposure
PUT /api/v1/camera/0/startexposure
    Duration=5.0&Light=true&ClientID=1&ClientTransactionID=1

# Move focuser
PUT /api/v1/focuser/0/move
    Position=5000&ClientID=1&ClientTransactionID=1
```

### Response Format

```json
{
  "Value": <result>,
  "ErrorNumber": 0,
  "ErrorMessage": "",
  "ClientTransactionID": 1,
  "ServerTransactionID": 1
}
```

---

## 7. Firmware Info

| Property | Value |
|----------|-------|
| Firmware version int | 2670 |
| Firmware version string | 6.70 |
| Force upgrade minimum | 2626 |
| Battery for update | 20% |
| ESP32-S3 mount firmware | Seestar_2.2.2.bin |
| Alpaca server version | 1.2.0-3 |
