"""Pydantic models for Seestar device state, settings, and protocol messages.

Models are derived from the decompiled Android app's @SerializedName annotations.
Field names use the JSON wire format (snake_case) as received from the device.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Protocol Messages ──────────────────────────────────────────────


class CommandRequest(BaseModel):
    """A JSON-RPC style command sent to the device."""

    id: int
    method: str
    params: dict[str, Any] | list[Any] | None = None


class CommandResponse(BaseModel):
    """A response from the device."""

    id: int = 0
    method: str = ""
    code: int = 0
    result: Any = None
    error: str | None = None


class EventMessage(BaseModel):
    """An asynchronous event from the device."""

    Event: str
    state: str | None = None
    code: int | None = None
    timestamp: str | None = None
    # Additional fields vary by event type and are captured in extra
    model_config = {"extra": "allow"}


# ── Discovery ──────────────────────────────────────────────────────


class DiscoveryResult(BaseModel):
    """Result from UDP device discovery (scan_iscope response)."""

    ssid: str = ""
    sn: str = ""
    model: str = ""
    bssid: str = ""
    pwd: str = ""
    serc: str = ""
    is_verified: bool = False
    product_model: str = ""
    tcp_client_num: int = 0


class DiscoveredDevice(BaseModel):
    """A discovered Seestar device on the network."""

    host: str
    port: int = 4700
    info: DiscoveryResult


# ── Device State Sub-models ────────────────────────────────────────


class SeestarDevice(BaseModel):
    """Device identification and capabilities."""

    name: str = ""
    sn: str = ""
    product_model: str = ""
    firmware_ver_int: int = 0
    firmware_ver_string: str = ""
    firmware_platform: int | None = None
    svr_ver_string: str = ""
    svr_ver_int: int = 0
    focal_len: float = 0.0
    fnumber: float | None = None
    is_verified: bool = False
    can_wide_cam_af: bool | None = None
    can_wide_cam_roi: bool | None = None
    can_star_mode_sel_cam: bool | None = None
    can_stop_one_view: bool | None = None

    model_config = {"extra": "allow"}


class SeestarMount(BaseModel):
    """Mount state."""

    tracking: bool = False
    close: bool | None = None
    move_type: str = ""
    equ_mode: bool = False

    model_config = {"extra": "allow"}


class SeestarCamera(BaseModel):
    """Camera hardware info."""

    chip_size: list[int] = Field(default_factory=list)
    debayer_pattern: str = ""
    focal_len: int = 0
    pixel_size_um: float = 0.0

    model_config = {"extra": "allow"}


class DeviceFocuser(BaseModel):
    """Focuser state."""

    step: int = 0
    max_step: int = 0
    state: str = "idle"

    model_config = {"extra": "allow"}


class SeestarPiStatus(BaseModel):
    """Raspberry Pi / SoC system status."""

    temp: float | None = None
    is_overtemp: bool | None = None
    is_undervolt: bool | None = None
    is_over_current: bool | None = None
    charger_status: str | None = None
    battery_capacity: int | None = None
    charge_online: bool | None = None
    is_typec_connected: bool | None = None
    battery_overtemp: bool | None = None
    battery_temp: float | None = None
    battery_temp_type: str | None = None
    arrival: bool | None = None

    model_config = {"extra": "allow"}


class SeestarAp(BaseModel):
    """WiFi access point settings."""

    ssid: str = ""
    passwd: str = ""
    is_5g: bool = False

    model_config = {"extra": "allow"}


class SeestarStation(BaseModel):
    """WiFi station (client) connection info."""

    server: bool | None = None
    freq: int | None = None
    ip: str | None = None
    ssid: str | None = None
    gateway: str | None = None
    netmask: str | None = None
    sig_lev: int | None = None
    flags: str | None = None
    key_mgmt: str = ""

    model_config = {"extra": "allow"}


class SeestarClient(BaseModel):
    """Connected client info."""

    model_config = {"extra": "allow"}


class SeeStarStorageVolume(BaseModel):
    """Storage volume info."""

    name: str = ""
    total: int = 0
    free: int = 0

    model_config = {"extra": "allow"}


class SeestarStorage(BaseModel):
    """Storage state."""

    is_typec_connected: bool = False
    connected_storage: list[str] = Field(default_factory=list)
    storage_volume: list[SeeStarStorageVolume] = Field(default_factory=list)
    cur_storage: str = ""

    model_config = {"extra": "allow"}


class SeestarBalanceSensor(BaseModel):
    """Balance sensor reading."""

    model_config = {"extra": "allow"}


class SeestarBalanceSensorResult(BaseModel):
    """Balance sensor result."""

    code: int = 0
    data: SeestarBalanceSensor | None = None

    model_config = {"extra": "allow"}


class SeestarCompassSensor(BaseModel):
    """Compass sensor reading."""

    model_config = {"extra": "allow"}


class SeestarCompassSensorResult(BaseModel):
    """Compass sensor result."""

    code: int = 0
    data: SeestarCompassSensor | None = None

    model_config = {"extra": "allow"}


# ── Settings Sub-models ────────────────────────────────────────────


class SeestarSettingMosaic(BaseModel):
    """Mosaic settings."""

    scale: float | None = None
    angle: int | None = None
    estimated_hours: float | None = None
    star_map_ratio: float | None = None
    star_map_angle: float | None = None

    model_config = {"extra": "allow"}


class SeestarSettingStack(BaseModel):
    """Stacking settings."""

    cont_capt: bool | None = None
    star_correction: bool | None = None
    drizzle2x: bool | None = None
    star_trails: bool | None = None
    airplane_line_removal: bool | None = None
    wide_denoise: bool | None = None

    model_config = {"extra": "allow"}


class SeestarSettingDither(BaseModel):
    """Dither settings."""

    model_config = {"extra": "allow"}


class SeestarSettingExpMs(BaseModel):
    """Exposure time settings."""

    model_config = {"extra": "allow"}


class SeestarSettingSecondCamera(BaseModel):
    """Second (wide-angle) camera settings."""

    ae_bri_percent: int | None = None
    wide_cross_offset: list[float] | None = None
    wide_cross_offset_show: list[float] | None = None

    model_config = {"extra": "allow"}


class SeestarSetting(BaseModel):
    """Device settings."""

    expert_mode: bool | None = None
    mosaic: SeestarSettingMosaic | None = None
    auto_3ppa_calib: bool | None = None
    wifi_country: str | None = None
    beep_volume: str | None = Field(None, alias="beep_volume")
    lang: str | None = None
    auto_exp: str | None = None
    ae_target_bri: int | None = None
    stack: SeestarSettingStack | None = None
    ae_bri_percent: float | None = None
    stack_after_goto: bool | None = None
    center_xy: list[int] | None = None
    heater_enable: bool | None = None
    stack_lenhance: bool | None = None  # lp_filter
    focal_pos: int | None = None
    factory_focal_pos: int | None = None
    exp_ms: SeestarSettingExpMs | None = None
    user_stack_sim: bool | None = None  # mock_mode
    usb_en_eth: bool | None = None
    auto_power_off: bool | None = None
    calibrate_location: bool | None = None
    rec_stablzn: bool | None = None
    manual_exp: bool | None = None
    isp_exp_ms: float | None = None
    isp_gain: float | None = None
    isp_gain_max: float | None = None
    isp_range_gain: list[float] | None = None
    isp_range_exp_us: list[float] | None = None
    isp_range_exp_us_scenery: list[float] | None = None
    expt_heater_enable: bool | None = None
    stack_dither: SeestarSettingDither | None = None
    dark_mode: bool | None = None
    ap_changed: bool | None = None
    guest_mode: bool | None = None
    rtsp_roi_index: int | None = None
    remote_joined: bool | None = None
    wide_4k: bool | None = None
    second_camera: SeestarSettingSecondCamera | None = None
    plan_target_af: bool | None = None
    viewplan_gohome: bool | None = None
    wide_cam: bool | None = None

    model_config = {"extra": "allow"}


# ── Composite Device State ─────────────────────────────────────────


class DeviceState(BaseModel):
    """Complete device state, returned by get_device_state."""

    device: SeestarDevice | None = None
    mount: SeestarMount | None = None
    camera: SeestarCamera | None = None
    second_camera: SeestarCamera | None = None
    focuser: DeviceFocuser | None = None
    second_focuser: DeviceFocuser | None = None
    ap: SeestarAp | None = None
    station: SeestarStation | None = None
    pi_status: SeestarPiStatus | None = None
    setting: SeestarSetting | None = None
    client: SeestarClient | None = None
    storage: SeestarStorage | None = None
    balance_sensor: SeestarBalanceSensorResult | None = None
    compass_sensor: SeestarCompassSensorResult | None = None

    model_config = {"extra": "allow"}


# ── View / Event State Models ──────────────────────────────────────


class ViewExposure(BaseModel):
    """Exposure event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewAutoFocus(BaseModel):
    """AutoFocus event state."""

    event: str = ""
    state: str = ""
    Exposure: ViewExposure | None = None
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewPlateSolve(BaseModel):
    """Plate solve event state."""

    state: str = ""
    error: str = ""
    code: int = 0
    ra_dec: list[float] | None = None
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewAutoGoto(BaseModel):
    """Auto goto event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewStack(BaseModel):
    """Stacking event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewAviRecord(BaseModel):
    """AVI recording event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewContinuousExposure(BaseModel):
    """Continuous exposure event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewRtsp(BaseModel):
    """RTSP streaming event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewObjectTrack(BaseModel):
    """Object tracking event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewGoPixel(BaseModel):
    """Go to pixel event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewInitialise(BaseModel):
    """Initialization event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewDarkLibrary(BaseModel):
    """Dark library event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class View3PPA(BaseModel):
    """3-point polar alignment event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewCheckPhotoMetry(BaseModel):
    """Photometry check event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewScanSunMoon(BaseModel):
    """Sun/Moon scan event state."""

    state: str = ""
    route: list[str] | None = None

    model_config = {"extra": "allow"}


class ViewData(BaseModel):
    """Primary view state, the main app state event payload."""

    state: str = ""
    mode: str = ""
    stage: str | None = None
    target_ra_dec: list[float] | None = None
    target_name: str = ""
    target_type: str = ""
    star_type: int = 0
    lp_filter: bool = False
    gain: int = 0
    planet_correction: bool | None = None
    scan_planet_tip: bool | None = None
    route: list[str] | None = None

    # Nested event states (CamelCase matches JSON keys)
    AviRecord: ViewAviRecord | None = None
    Stack: ViewStack | None = None
    ContinuousExposure: ViewContinuousExposure | None = None
    AutoGoto: ViewAutoGoto | None = None
    RTSP: ViewRtsp | None = None
    ObjectTrack: ViewObjectTrack | None = None
    AutoFocus: ViewAutoFocus | None = None
    GoPixel: ViewGoPixel | None = None
    Initialise: ViewInitialise | None = None
    DarkLibrary: ViewDarkLibrary | None = None
    CheckPhotoMetry: ViewCheckPhotoMetry | None = None
    ScanSun: ViewScanSunMoon | None = None

    # Uses alias for JSON field "3PPA" which isn't a valid Python identifier
    three_ppa: View3PPA | None = Field(None, alias="3PPA")

    model_config = {"extra": "allow", "populate_by_name": True}


# ── Coordinate Types ───────────────────────────────────────────────


class EquatorialCoord(BaseModel):
    """Equatorial coordinates."""

    ra: float = 0.0
    dec: float = 0.0


class HorizontalCoord(BaseModel):
    """Horizontal (alt-az) coordinates."""

    alt: float = 0.0
    az: float = 0.0


class SolveResult(BaseModel):
    """Plate solve result."""

    ra_dec: list[float] | None = None
    code: int = 0
    error: str = ""
    state: str = ""

    model_config = {"extra": "allow"}
