"""Constants extracted from ZWO Seestar Android app v3.0.2.

Port numbers, command method strings, event types, control types,
and state enumerations for the Seestar telescope control protocol.
"""

from enum import IntEnum, StrEnum

# ── Ports ──────────────────────────────────────────────────────────

COMMAND_PORT = 4700          # Main JSON command/response TCP socket
RTMP_PORT = 4554             # RTMP video stream (telephoto)
RTMP_WIDE_PORT = 4555        # RTMP video stream (wide-angle)
IMAGE_PORT = 4800            # Live image stream (telephoto)
IMAGE_WIDE_PORT = 4804       # Live image stream (wide-angle)
FILE_PORT = 4801             # File transfer
FW_COMMAND_PORT = 4350       # Firmware update command socket
FW_UPLOAD_PORT = 4361        # Firmware upload socket
DISCOVERY_PORT = 4720        # UDP discovery broadcast

# ── Heartbeat ──────────────────────────────────────────────────────

HEARTBEAT_INTERVAL = 4.0     # seconds
HEARTBEAT_METHOD = "test_connection"

# ── Firmware ───────────────────────────────────────────────────────

FIRMWARE_VERSION_INT = 2732
FIRMWARE_VERSION_NAME = "7.32"
FIRMWARE_FORCE_UPGRADE_MIN = 2626
BATTERY_FOR_UPDATE_FW = 20

# ── Device Models ──────────────────────────────────────────────────

class DeviceModel(StrEnum):
    S30 = "S30"
    S50 = "S50"
    S30_PRO = "S30Pro"
    S30_PLUS = "S30Plus"
    S50_PRO = "S50Pro"


# ── Event Parent Types ─────────────────────────────────────────────

class EventCategory(StrEnum):
    APP_STATE = "APP_STATE"
    DEVICE_STATE = "DEVICE_STATE"
    OTHER = "OTHER"


# ── Event Types ────────────────────────────────────────────────────
# Wire values from EventType.java

class EventType(StrEnum):
    # APP_STATE events
    SELECT_CAMERA = "SelectCamera"
    VIEW = "View"
    SECOND_VIEW = "SecondView"
    INITIALISE = "Initialise"
    DARK_LIBRARY = "DarkLibrary"
    THREE_PPA = "3PPA"
    CONTINUOUS_EXPOSURE = "ContinuousExposure"
    STACK = "Stack"
    AVI_RECORD = "AviRecord"
    VIEW_PLAN = "ViewPlan"
    TARGET = "Target"
    AUTO_GOTO = "AutoGoto"
    SCOPE_GOTO = "ScopeGoto"
    EXPOSURE = "Exposure"
    PLATE_SOLVE = "PlateSolve"
    RTSP = "RTSP"
    OBJECT_TRACK = "ObjectTrack"
    AUTO_FOCUS = "AutoFocus"
    FOCUSER_MOVE = "FocuserMove"
    GO_PIXEL = "GoPixel"
    SCAN_SUN_MOON = "ScanSun"
    CHECK_PHOTOMETRY = "CheckPhotoMetry"
    # DEVICE_STATE events
    PI_STATUS = "PiStatus"
    DISK_SPACE = "DiskSpace"
    CLIENT = "Client"
    SETTING = "Setting"
    SCOPE_HOME = "ScopeHome"
    SCOPE_MOVE_TO_HORIZON = "ScopeMoveToHorizon"
    MOUNT_MODE = "MountMode"
    WHEEL_MOVE = "WheelMove"
    # OTHER events
    SAVE_IMAGE = "SaveImage"
    ALERT = "Alert"
    UNKNOWN = "Unknown"


EVENT_CATEGORIES: dict[EventType, EventCategory] = {
    EventType.SELECT_CAMERA: EventCategory.APP_STATE,
    EventType.VIEW: EventCategory.APP_STATE,
    EventType.SECOND_VIEW: EventCategory.APP_STATE,
    EventType.INITIALISE: EventCategory.APP_STATE,
    EventType.DARK_LIBRARY: EventCategory.APP_STATE,
    EventType.THREE_PPA: EventCategory.APP_STATE,
    EventType.CONTINUOUS_EXPOSURE: EventCategory.APP_STATE,
    EventType.STACK: EventCategory.APP_STATE,
    EventType.AVI_RECORD: EventCategory.APP_STATE,
    EventType.VIEW_PLAN: EventCategory.APP_STATE,
    EventType.TARGET: EventCategory.APP_STATE,
    EventType.AUTO_GOTO: EventCategory.APP_STATE,
    EventType.SCOPE_GOTO: EventCategory.APP_STATE,
    EventType.EXPOSURE: EventCategory.APP_STATE,
    EventType.PLATE_SOLVE: EventCategory.APP_STATE,
    EventType.RTSP: EventCategory.APP_STATE,
    EventType.OBJECT_TRACK: EventCategory.APP_STATE,
    EventType.AUTO_FOCUS: EventCategory.APP_STATE,
    EventType.FOCUSER_MOVE: EventCategory.APP_STATE,
    EventType.GO_PIXEL: EventCategory.APP_STATE,
    EventType.SCAN_SUN_MOON: EventCategory.APP_STATE,
    EventType.CHECK_PHOTOMETRY: EventCategory.APP_STATE,
    EventType.PI_STATUS: EventCategory.DEVICE_STATE,
    EventType.DISK_SPACE: EventCategory.DEVICE_STATE,
    EventType.CLIENT: EventCategory.DEVICE_STATE,
    EventType.SETTING: EventCategory.DEVICE_STATE,
    EventType.SCOPE_HOME: EventCategory.DEVICE_STATE,
    EventType.SCOPE_MOVE_TO_HORIZON: EventCategory.DEVICE_STATE,
    EventType.MOUNT_MODE: EventCategory.DEVICE_STATE,
    EventType.WHEEL_MOVE: EventCategory.DEVICE_STATE,
    EventType.SAVE_IMAGE: EventCategory.OTHER,
    EventType.ALERT: EventCategory.OTHER,
    EventType.UNKNOWN: EventCategory.OTHER,
}

# ── Additional Event Constants from MainCameraConstants ────────────
# These appear in JSON payloads but are not in the EventType enum

EVENT_BATCH_STACK = "BatchStack"
EVENT_PLANET_STACK = "PlanetStack"
EVENT_BALANCE_SENSOR = "BalanceSensor"
EVENT_CAMERA_STATE_CHANGE = "CameraStateChange"
EVENT_COOL_WORKING = "cooling"
EVENT_COOLER_POWER = "CoolerPower"
EVENT_COOL_TOO_SLOW = "CoolTooSlow"
EVENT_CREATE_CALIB_FRAME = "CreateCalibFrame"
EVENT_CREATE_HPC = "CreateHPC"
EVENT_DEVICE_CHANGE = "DeviceChange"
EVENT_DITHER = "Dither"
EVENT_EQ_MODE_PA = "EqModePA"
EVENT_EXPORT_IMAGE = "ExportImage"
EVENT_EXPOSURE_TAG = "ExposureTag"
EVENT_FIND_STAR = "FindStar"
EVENT_FIRST_DELAY = "FirstDelay"
EVENT_FRAME_DELAY = "FrameDelay"
EVENT_GUIDING_DITHERED = "GuidingDithered"
EVENT_LOOPING_FRAMES = "LoopingFrames"
EVENT_MERIDIAN_FLIP = "MeridianFlip"
EVENT_NGINX = "Nginx"
EVENT_PLAYBACK_RTMP = "AviRtmp"
EVENT_RESTART_GUIDE = "RestartGuide"
EVENT_RTMP = "RTMP"
EVENT_SCENERY = "scenery"
EVENT_SCOPE_TRACK = "ScopeTrack"
EVENT_SEQUENCE = "Sequence"
EVENT_SETTLE = "Settle"
EVENT_STACKING = "stacking"
EVENT_STACK_EXP_LOOP = "StackExpLoop"
EVENT_STATION = "Station"
EVENT_TARGET_DELAY = "TargetDelay"
EVENT_TEMPERATURE = "Temperature"
EVENT_VERSION = "Version"
EVENT_WARNING = "Warning"
EVENT_WHEEL_CALIBRATE = "WheelCalibrate"
EVENT_WIDE_CROSS_OFFSET = "wide_cross_offset"
EVENT_BATT_HI_TEMP_SHUTDOWN = "BattHiTempShutdown"
EVENT_DISK_EJECT = "DiskEject"
EVENT_ALIGN = "Align"
EVENT_ANNOTATE = "Annotate"
EVENT_AI_PROCESS = "AIProcess"
EVENT_AUTO_EXP = "AutoExp"
EVENT_AUTO_GOTO_3PPA = "AutoGoto_3ppa"
EVENT_AUTO_GOTO_STEP = "AutoGotoStep"
EVENT_CALIB_GSENSOR = "CalibGSensor"
EVENT_SEND_STOPPED = "SendStopped"


# ── Camera States ──────────────────────────────────────────────────

class CameraState(StrEnum):
    IDLE = "idle"
    EXPOSING = "exposing"
    EXPOSE = "expose"
    DOWNLOAD = "download"
    COOLING = "cooling"
    CLOSED = "close"
    ERROR = "error"
    FIRST_DELAY = "first_delay"
    FRAME_DELAY = "frame_delay"
    TARGET_DELAY = "target_delay"
    GUIDE_SETTLING = "guide_settling"
    DITHER_SETTLING = "dither_settling"
    MERIDIAN_FLIP = "meridian_flip"
    CHANGE_TARGET = "change_target"


# ── Focuser States ─────────────────────────────────────────────────

class FocuserState(StrEnum):
    IDLE = "idle"
    MOVING = "moving"
    CLOSED = "close"


# ── Filter Wheel States ───────────────────────────────────────────

class WheelState(StrEnum):
    IDLE = "idle"
    MOVING = "moving"
    CALIBRATING = "calibrating"
    CLOSED = "close"
    ERROR = "error"


# ── Control Types ──────────────────────────────────────────────────
# Used with get_control_value / set_control_value

class ControlType(StrEnum):
    EXPOSURE = "Exposure"
    GAIN = "Gain"
    OFFSET = "Offset"
    RED = "Red"
    BLUE = "Blue"
    HARDWARE_BIN = "HardwareBin"
    MONO_BIN = "MonoBin"
    COOLER_ON = "CoolerOn"
    COOL_POWER_PERC = "CoolPowerPerc"
    TARGET_TEMP = "TargetTemp"
    TEMPERATURE = "Temperature"
    ANTI_DEW_HEATER = "AntiDewHeater"
    FRAME_SIZE = "FrameSize"
    ISO = "ISO"
    BATTERY_LEVEL = "batterylevel"
    CABLE_SNAP = "cablesnap"
    CAPTURE_TARGET = "capturetarget"
    PREVIEW_ZOOM = "previewzoom"
    ZOOM_POSITION = "zoomposition"


# ── Auto Focus Triggers ───────────────────────────────────────────

class AutoFocusTrigger(IntEnum):
    MANUAL = 0
    TEMP_CHANGE = 1
    TIME_CHANGE = 2
    WHEEL_CHANGE = 3
    BEFORE_CAPTURE_CHANGE = 4
    MERIDIAN_FLIP_CHANGE = 5
    CONTINUE_CHANGE = 6


# ── Auto Goto Functions ───────────────────────────────────────────

class AutoGotoFunc(StrEnum):
    RA_DEC = "goto_ra_dec"
    PIXEL = "goto_pix"
    MERIDIAN_FLIP = "merid_flip"


# ── Page Modes ─────────────────────────────────────────────────────

class PageMode(StrEnum):
    PREVIEW = "preview"
    STACK = "stack"
    FOCUS = "focus"
    POLAR_ALIGN = "pa"
    PLAN = "plan"
    RTMP = "rtmp"
    AUTOSAVE = "autosave"


# ── Volume Modes ───────────────────────────────────────────────────

class VolumeMode(StrEnum):
    BACKYARD = "backyard"
    FIELD = "field"
    CLOSE = "close"


# ── Command Method Strings ─────────────────────────────────────────
# All wire method names organized by subsystem.
# Each maps to the JSON "method" field in protocol messages.

class Cmd:
    """All command method strings organized by subsystem."""

    # ── Handshake / Auth ──
    GET_VERIFY_STR = "get_verify_str"
    VERIFY_CLIENT = "verify_client"
    PI_IS_VERIFIED = "pi_is_verified"
    PI_ENCRYPT = "pi_encrypt"

    # ── Heartbeat ──
    TEST_CONNECTION = "test_connection"

    # ── Discovery ──
    SCAN_AIR = "scan_air"

    # ── System / Device ──
    GET_DEVICE_STATE = "get_device_state"
    GET_APP_STATE = "iscope_get_app_state"
    CLEAR_APP_STATE = "clear_app_state"
    GET_FUNC_STATE = "get_func_state"
    PI_SHUTDOWN = "pi_shutdown"
    PI_REBOOT = "pi_reboot"
    PI_GET_INFO = "pi_get_info"
    PI_GET_TIME = "pi_get_time"
    PI_SET_TIME = "pi_set_time"
    PLAY_SOUND = "play_sound"
    CHARGE_ONLY = "charge_only"
    IS_DOWNGRADED = "is_downgraded"
    CLEAR_DOWNGRADE = "clear_downgrade"
    NEED_REBOOT = "need_reboot"
    CHECK_INTERNET = "check_internet"
    GET_SERVER_LOG = "get_server_log"

    # ── Network / WiFi ──
    PI_SET_AP = "pi_set_ap"
    PI_GET_AP = "pi_get_ap"
    PI_SET_5G = "pi_set_5g"
    PI_STATION_OPEN = "pi_station_open"
    PI_STATION_CLOSE = "pi_station_close"
    PI_STATION_SCAN = "pi_station_scan"
    PI_STATION_LIST = "pi_station_list"
    PI_STATION_SET = "pi_station_set"
    PI_STATION_SELECT = "pi_station_select"
    PI_STATION_REMOVE = "pi_station_remove"
    PI_STATION_STATE = "pi_station_state"
    PI_STATION_AUTO_CONNECT = "pi_station_auto_connect"
    PI_ETH0_STATE = "pi_eth0_state"
    PI_SET_ETH0 = "pi_set_eth0"

    # ── Power ──
    PI_OUTPUT_SET2 = "pi_output_set2"
    PI_OUTPUT_GET2 = "pi_output_get2"
    GET_POWER_SUPPLY = "get_power_supply"

    # ── Mount / Scope ──
    SCOPE_GET_EQU_COORD = "scope_get_equ_coord"
    SCOPE_GET_HORIZ_COORD = "scope_get_horiz_coord"
    SCOPE_GET_STATE = "scope_get_state"
    SCOPE_GET_TRACK_STATE = "scope_get_track_state"
    SCOPE_SET_TRACK_STATE = "scope_set_track_state"
    SCOPE_SPEED_MOVE = "scope_speed_move"
    SCOPE_MOVE = "scope_move"  # also used as abort slew
    SCOPE_PARK = "scope_park"
    SCOPE_SYNC = "scope_sync"
    SCOPE_SET_LOCATION = "scope_set_location"
    SCOPE_SET_TIME = "scope_set_time"
    SCOPE_SET_EQ_MODE = "scope_set_eq_mode"
    SCOPE_MOVE_TO_HORIZON = "scope_move_to_horizon"
    SCOPE_SYNC_PLANET = "scope_sync_planet"
    SCOPE_GET_BEEP_VOLUME = "scope_get_beep_volume"
    SCOPE_SET_BEEP_VOLUME = "scope_set_beep_volume"
    START_AUTO_GOTO = "start_auto_goto"
    STOP_AUTO_GOTO = "stop_auto_goto"
    START_AUTO_GOTO_PIXEL = "start_auto_goto_pixel"
    GET_MERID_DELTA = "get_merid_delta"
    GET_MERID_SETTING = "get_merid_setting"
    SET_MERID_SETTING = "set_merid_setting"
    SET_USER_LOCATION = "set_user_location"
    GET_USER_LOCATION = "get_user_location"
    CALI_USER_LOCATION = "cali_user_location"

    # ── Camera ──
    OPEN_CAMERA = "open_camera"
    CLOSE_CAMERA = "close_camera"
    GET_CAMERA_INFO = "get_camera_info"
    GET_CAMERA_STATE = "get_camera_state"
    GET_CAMERA_BIN = "get_camera_bin"
    GET_CAMERA_EXP_AND_BIN = "get_camera_exp_and_bin"
    SET_CAMERA_BIN = "set_camera_bin"
    GET_CONTROLS = "get_controls"
    GET_CONTROL_VALUE = "get_control_value"
    SET_CONTROL_VALUE = "set_control_value"
    START_EXPOSURE = "start_exposure"
    STOP_EXPOSURE = "stop_exposure"
    START_CONTINUOUS_EXPOSE = "start_continuous_expose"
    CAN_ABORT_EXPOSE = "can_abort_expose"
    GET_CONNECTED_CAMERAS = "get_connected_cameras"
    GET_GAIN_SEGMENT = "get_gain_segment"
    GET_SUBFRAME = "get_subframe"
    SET_SUBFRAME = "set_subframe"
    SAVE_IMAGE = "save_image"
    SAVE_STACK = "save_stack"
    FITS_TO_JPG = "fits_to_jpg"

    # ── Focuser ──
    OPEN_FOCUSER = "open_focuser"
    CLOSE_FOCUSER = "close_focuser"
    MOVE_FOCUSER = "move_focuser"
    STOP_FOCUSER = "stop_focuser"
    START_AUTO_FOCUS = "start_auto_focuse"
    STOP_AUTO_FOCUS = "stop_auto_focuse"
    GET_FOCUSER_POSITION = "get_focuser_position"
    GET_FOCUSER_STATE = "get_focuser_state"
    GET_FOCUSER_VALUE = "get_focuser_value"
    GET_FOCUSER_SETTING = "get_focuser_setting"
    SET_FOCUSER_SETTING = "set_focuser_setting"
    GET_CONNECTED_FOCUSER = "get_connected_focuser"
    GET_AUTO_FOCUS_IMG = "get_auto_focus_img"
    RESET_FACTORY_FOCAL_POS = "reset_factory_focal_pos"
    GET_FOCAL_LENGTH = "get_focal_length"
    SET_FOCAL_LENGTH = "set_focal_length"

    # ── Filter Wheel ──
    OPEN_WHEEL = "open_wheel"
    CLOSE_WHEEL = "close_wheel"
    GET_WHEEL_POSITION = "get_wheel_position"
    SET_WHEEL_POSITION = "set_wheel_position"
    GET_WHEEL_STATE = "get_wheel_state"
    GET_WHEEL_SETTING = "get_wheel_setting"
    SET_WHEEL_SETTING = "set_wheel_setting"
    GET_WHEEL_SLOT_NAME = "get_wheel_slot_name"
    SET_WHEEL_SLOT_NAME = "set_wheel_slot_name"
    SET_WHEEL_UNIDIRECTION = "set_wheel_unidirection"
    CALIBRATE_WHEEL = "calibrate_wheel"
    GET_CONNECTED_WHEELS = "get_connected_wheels"

    # ── View / Preview ──
    START_VIEW = "iscope_start_view"
    STOP_VIEW = "iscope_stop_view"
    CANCEL_VIEW = "iscope_cancel_view"
    GET_VIEW_STATE = "get_view_state"

    # ── Stacking ──
    START_STACK = "iscope_start_stack"
    START_BATCH_STACK = "start_batch_stack"
    STOP_BATCH_STACK = "stop_batch_stack"
    CLEAR_BATCH_STACK = "clear_batch_stack"
    START_PLANET_STACK = "start_planet_stack"
    STOP_PLANET_STACK = "stop_planet_stack"
    CLEAR_PLANET_STACK = "clear_planet_stack"
    CLEAR_STACK = "clear_stack"
    IS_STACKED = "is_stacked"
    GET_STACK_INFO = "get_stack_info"
    GET_STACK_SETTING = "get_stack_setting"
    SET_STACK_SETTING = "set_stack_setting"
    SET_STACK_TYPE = "set_stack_type"
    GET_BATCH_STACK_SETTING = "get_batch_stack_setting"
    SET_BATCH_STACK_SETTING = "set_batch_stack_setting"
    GET_BATCH_STACK_THUMBNAIL = "get_batch_stack_thumbnail"
    DEL_BATCH_STACK_FILE = "del_batch_stack_file"
    USER_STACK_SIM = "user_stack_sim"
    GET_STACKED_IMG = "get_stacked_img"

    # ── Plate Solving ──
    START_SOLVE = "start_solve"
    STOP_SOLVE = "stop_solve"
    GET_SOLVE_RESULT = "get_solve_result"
    GET_LAST_SOLVE_RESULT = "get_last_solve_result"

    # ── Image Management ──
    GET_IMG_FILE = "get_img_file"
    GET_IMG_FILE_INFO = "get_img_file_info"
    SET_IMG_FILE_INFO = "set_img_file_info"
    GET_IMG_THUMBNAIL = "get_img_thumbnail"
    GET_IMG_FILE_IN_JPG = "get_img_file_in_jpg"
    GET_IMG_FILE_PAGE_NAME = "get_img_file_page_name"
    GET_IMG_FILE_PAGE_NUMBER = "get_img_file_page_number"
    GET_IMG_PAGE_THUMBNAIL = "get_img_page_thumbnail"
    GET_FITS_FILE = "get_fits_file"
    GET_CURRENT_IMG = "get_current_img"
    DELETE_IMAGE = "delete_image"
    DELETE_ALL_IMAGE = "delete_all_image"
    FILE_RENAME = "file_rename"
    REMOVE_FILE = "remove_file"
    IS_IMG_FILE_ANNOTATED = "is_img_file_annotated"
    SET_IS_FAVORITE = "set_is_favorite"
    GET_ALBUMS = "get_albums"
    GET_IMAGE_SAVE_PATH = "get_image_save_path"
    SET_IMAGE_SAVE_PATH = "set_image_save_path"
    GET_IMG_NAME_FIELD = "get_img_name_field"
    SET_IMG_NAME_FIELD = "set_img_name_field"

    # ── Streaming ──
    BEGIN_STREAMING = "begin_streaming"
    STOP_STREAMING = "stop_streaming"
    START_RECORD_AVI = "start_record_avi"
    STOP_RECORD_AVI = "stop_record_avi"
    START_AVI_RTMP = "start_avi_rtmp"
    STOP_AVI_RTMP = "stop_avi_rtmp"
    GET_RTMP_CONFIG = "get_rtmp_config"
    SET_RTMP_CONFIG = "set_rtmp_config"

    # ── Polar Alignment ──
    START_POLAR_ALIGN = "start_polar_align"
    STOP_POLAR_ALIGN = "stop_polar_align"
    PAUSE_POLAR_ALIGN = "pause_polar_align"
    CLEAR_POLAR_ALIGN = "clear_polar_align"
    CHECK_PA_ALT = "check_pa_alt"
    GET_POLAR_ALIGN_IMAGE = "get_polar_align_image"
    SET_POLAR_ALIGN_IMAGE = "set_polar_align_image"
    RM_POLAR_ALIGN_IMAGE = "rm_polar_align_image"
    GET_POLAR_AXIS = "get_polar_axis"
    GET_3P_PA_SETTING = "get_3p_pa_setting"
    SET_3P_PA_SETTING = "set_3p_pa_setting"
    GET_3P_PA_STATE = "get_3p_pa_state"

    # ── Compass / Sensors ──
    START_COMPASS_CALIBRATION = "start_compass_calibration"
    STOP_COMPASS_CALIBRATION = "stop_compass_calibration"
    GET_COMPASS_STATE = "get_compass_state"
    START_GSENSOR_CALIBRATION = "start_gsensor_calibration"

    # ── Annotation / AI ──
    START_ANNOTATE = "start_annotate"
    STOP_ANNOTATE = "stop_annotate"
    START_AI_PROCESS = "start_ai_process"
    CHECK_AI_PROCESS = "check_ai_process"
    STOP_FUNC = "stop_func"
    START_FIND_STAR = "start_find_star"
    STOP_FIND_STAR = "stop_find_star"
    GET_FIND_STAR_RESULT = "get_find_star_result"

    # ── Planning / Sequence ──
    LIST_PLAN = "list_plan"
    GET_PLAN = "get_plan"
    SET_PLAN = "set_plan"
    DELETE_PLAN = "delete_plan"
    IMPORT_PLAN = "import_plan"
    CLEAR_PLAN = "clear_plan"
    RESET_PLAN = "reset_plan"
    GET_ENABLED_PLAN = "get_enabled_plan"
    GET_VIEW_PLAN = "get_view_plan"
    SET_VIEW_PLAN = "set_view_plan"
    CLEAR_VIEW_PLAN = "clear_view_plan"
    SET_SEQUENCE = "set_sequence"
    GET_SEQUENCE_SETTING = "get_sequence_setting"
    SET_SEQUENCE_SETTING = "set_sequence_setting"
    DELETE_SEQUENCE = "delete_sequence"
    CLEAR_SEQUENCE = "clear_sequence"
    RESET_SEQUENCE_PROGRESS = "reset_sequence_progress"
    GET_TARGET_SEQUENCES = "get_target_sequences"

    # ── Settings ──
    GET_SETTING = "get_setting"
    SET_SETTING = "set_setting"
    GET_APP_SETTING = "get_app_setting"
    SET_APP_SETTING = "set_app_setting"
    GET_TEST_SETTING = "get_test_setting"
    SET_TEST_SETTING = "set_test_setting"

    # ── Calibration Frames ──
    GET_CALIB_FRAME = "get_calib_frame"
    SET_CALIB_FRAME = "set_calib_frame"
    GET_CALIB_PARAM = "get_calib_param"
    SET_CALIB_PARAM = "set_calib_param"
    START_CREATE_CALIB_FRAME = "start_create_calib_frame"
    START_CREATE_DARK = "start_create_dark"
    START_CREATE_HPC = "start_create_hpc"

    # ── Dither ──
    GET_DITHER = "get_dither"
    SET_DITHER = "set_dither"

    # ── Remote ──
    REMOTE_JOIN = "remote_join"
    REMOTE_DISJOIN = "remote_disjoin"
    REMOTE_DISCONNECT = "remote_disconnect"

    # ── Storage ──
    GET_DISK_VOLUME = "get_disk_volume"
    CAN_FORMAT_EMMC = "can_format_emmc"
    FORMAT_EMMC = "format_emmc"
    EJECT_DISK = "eject_disk"

    # ── Export ──
    START_EXPORT_IMAGE = "start_export_image"
    STOP_EXPORT_IMAGE = "stop_export_image"

    # ── Misc ──
    START_DEMONSTRATE = "start_demonstrate"
    STOP_DEMONSTRATE = "stop_demonstrate"
    SET_PAGE = "set_page"
    GET_COMET_POSITION = "get_comet_position"
    GET_PLANET_POSITION = "get_planet_position"
    UPDATE_COMET_TXT = "update_comet_txt"
    START_SCAN_PLANET = "start_scan_planet"
    START_TRACK_OBJECT = "start_track_object"
    CHECK_PHOTOMETRY = "check_photometry"
    GET_PHOTOMETRY_RESULT = "get_photometry_result"
    GET_PHOTOMETRY_STARS = "get_photometry_stars"
    GET_PHOTOMETRY_PLOT = "get_photometry_plot"
    SET_PHOTOMETRY = "set_photometry"

    # ── Scope diagnostics (3.1.2+) ──
    SCOPE_SEND_CMD = "scope_send_cmd"
    SCOPE_GET_TEST_DATE = "scope_get_test_date"
    CLEAR_AUTOSAVE_ERR = "clear_autosave_err"
    EXPT_SET_HEATER_ENABLE = "expt_set_heater_enable"
    SET_WIFI_COUNTRY = "set_wifi_country"
    START_FUNC = "start_func"

    # ── Custom Object Lists ──
    ADD_LIST = "add_list"
    DEL_LIST = "del_list"
    RENAME_LIST = "rename_list"
    GET_LIST = "get_list"
    ADD_OBJ = "add_obj"
    DEL_OBJ = "del_obj"
    GET_OBJ = "get_obj"

    # ── Firmware Update ──
    BEGIN_RECV = "begin_recv"

    # ── Voice ──
    APP_VOICE_STATE = "app_voice_state"
    APP_VOICE_STATE_DOWNLOAD = "app_voice_state_download"
