"""High-level command builders organized by subsystem.

Each subsystem is a descriptor class that gets attached to SeestarClient,
providing `client.mount.get_equ_coord()`, `client.camera.start_exposure()`, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .constants import Cmd, ControlType
from .models import CommandResponse, DeviceState, EquatorialCoord, HorizontalCoord, SolveResult

if TYPE_CHECKING:
    from .client import SeestarClient


class _Subsystem:
    """Base class for command subsystems bound to a client."""

    def __init__(self, client: SeestarClient) -> None:
        self._client = client

    async def _cmd(
        self, method: str, params: dict[str, Any] | None = None, **kw: Any
    ) -> CommandResponse:
        return await self._client.send_command(method, params, **kw)


# ── Mount ──────────────────────────────────────────────────────────


class MountCommands(_Subsystem):
    """Mount/scope control commands."""

    async def get_equ_coord(self) -> EquatorialCoord:
        """Get current RA/Dec equatorial coordinates."""
        resp = await self._cmd(Cmd.SCOPE_GET_EQU_COORD)
        r = resp.result or {}
        return EquatorialCoord(ra=r.get("ra", 0.0), dec=r.get("dec", 0.0))

    async def get_horiz_coord(self) -> HorizontalCoord:
        """Get current Alt/Az horizontal coordinates."""
        resp = await self._cmd(Cmd.SCOPE_GET_HORIZ_COORD)
        r = resp.result or {}
        return HorizontalCoord(alt=r.get("alt", 0.0), az=r.get("az", 0.0))

    async def get_state(self) -> CommandResponse:
        """Get mount state."""
        return await self._cmd(Cmd.SCOPE_GET_STATE)

    async def get_track_state(self) -> bool:
        """Get tracking state."""
        resp = await self._cmd(Cmd.SCOPE_GET_TRACK_STATE)
        return bool(resp.result)

    async def set_track_state(self, tracking: bool) -> CommandResponse:
        """Enable or disable sidereal tracking."""
        return await self._cmd(Cmd.SCOPE_SET_TRACK_STATE, tracking)

    async def speed_move(
        self, angle: int, percent: int = 50, level: int = 1, dur_sec: int = 3
    ) -> CommandResponse:
        """Move at a given speed and angle.

        Args:
            angle: Movement angle in degrees.
            percent: Speed percentage (0-100).
            level: Speed level.
            dur_sec: Duration in seconds.
        """
        return await self._cmd(
            Cmd.SCOPE_SPEED_MOVE,
            {"angle": angle, "percent": percent, "level": level, "dur_sec": dur_sec},
        )

    async def abort_slew(self) -> CommandResponse:
        """Abort the current slew/goto."""
        return await self._cmd(Cmd.SCOPE_MOVE, ["none"])

    async def park(self) -> CommandResponse:
        """Park the mount (move to home position)."""
        return await self._cmd(Cmd.SCOPE_PARK)

    async def sync(self, ra: float, dec: float) -> CommandResponse:
        """Sync mount to given coordinates."""
        return await self._cmd(Cmd.SCOPE_SYNC, {"ra": ra, "dec": dec})

    async def set_location(self, lat: float, lon: float, alt: float = 0.0) -> CommandResponse:
        """Set observer location."""
        return await self._cmd(
            Cmd.SCOPE_SET_LOCATION, {"lat": lat, "lon": lon, "alt": alt}
        )

    async def set_time(self, timestamp: int) -> CommandResponse:
        """Set device time (Unix timestamp)."""
        return await self._cmd(Cmd.SCOPE_SET_TIME, {"timestamp": timestamp})

    async def set_eq_mode(self, enabled: bool) -> CommandResponse:
        """Set equatorial mount mode."""
        return await self._cmd(Cmd.SCOPE_SET_EQ_MODE, {"equ_mode": enabled})

    async def move_to_horizon(self) -> CommandResponse:
        """Move mount to horizon position."""
        return await self._cmd(Cmd.SCOPE_MOVE_TO_HORIZON)

    async def goto(
        self,
        ra: float,
        dec: float,
        target_name: str = "",
        mode: str = "star",
        lp_filter: bool = False,
    ) -> CommandResponse:
        """Start an auto goto to the given RA/Dec.

        Args:
            ra: Right Ascension in hours.
            dec: Declination in degrees.
            target_name: Name of the target.
            mode: Target mode ("star", "dso", etc.).
            lp_filter: Enable light pollution filter.
        """
        return await self._cmd(
            Cmd.START_AUTO_GOTO,
            {"ra": ra, "dec": dec, "target_name": target_name, "mode": mode, "lp_filter": lp_filter},
        )

    async def stop_goto(self) -> CommandResponse:
        """Stop the current auto goto."""
        return await self._cmd(Cmd.STOP_AUTO_GOTO)

    async def get_merid_setting(self) -> CommandResponse:
        """Get meridian flip settings."""
        return await self._cmd(Cmd.GET_MERID_SETTING)

    async def set_merid_setting(self, **params: Any) -> CommandResponse:
        """Set meridian flip settings."""
        return await self._cmd(Cmd.SET_MERID_SETTING, params)

    async def set_user_location(self, lat: float, lon: float) -> CommandResponse:
        """Set user geographic location."""
        return await self._cmd(Cmd.SET_USER_LOCATION, {"lat": lat, "lon": lon})

    async def get_user_location(self) -> CommandResponse:
        """Get user geographic location."""
        return await self._cmd(Cmd.GET_USER_LOCATION)

    async def calibrate_user_location(self) -> CommandResponse:
        """Calibrate user location using star horizon data (3.1.2+)."""
        return await self._cmd(Cmd.CALI_USER_LOCATION)

    async def scope_send_cmd(self, cmd: str, **params: Any) -> CommandResponse:
        """Send a raw command directly to the mount controller (3.1.2+).

        Args:
            cmd: Mount controller command string.
            **params: Additional parameters for the command.
        """
        return await self._cmd(Cmd.SCOPE_SEND_CMD, {"cmd": cmd, **params})


# ── Camera ─────────────────────────────────────────────────────────


class CameraCommands(_Subsystem):
    """Camera control commands."""

    async def open(self) -> CommandResponse:
        """Open the camera."""
        return await self._cmd(Cmd.OPEN_CAMERA)

    async def close(self) -> CommandResponse:
        """Close the camera."""
        return await self._cmd(Cmd.CLOSE_CAMERA)

    async def get_info(self) -> CommandResponse:
        """Get camera hardware info."""
        return await self._cmd(Cmd.GET_CAMERA_INFO)

    async def get_state(self) -> CommandResponse:
        """Get camera state."""
        return await self._cmd(Cmd.GET_CAMERA_STATE)

    async def get_control_value(self, control: str | ControlType) -> CommandResponse:
        """Get a camera control value (e.g. Gain, Exposure)."""
        return await self._cmd(Cmd.GET_CONTROL_VALUE, {"type": str(control)})

    async def set_control_value(self, control: str | ControlType, value: Any) -> CommandResponse:
        """Set a camera control value."""
        return await self._cmd(Cmd.SET_CONTROL_VALUE, {"type": str(control), "value": value})

    async def start_exposure(self) -> CommandResponse:
        """Start a single exposure."""
        return await self._cmd(Cmd.START_EXPOSURE)

    async def stop_exposure(self) -> CommandResponse:
        """Stop the current exposure."""
        return await self._cmd(Cmd.STOP_EXPOSURE)

    async def start_continuous_expose(self) -> CommandResponse:
        """Start continuous exposures."""
        return await self._cmd(Cmd.START_CONTINUOUS_EXPOSE)

    async def get_controls(self) -> CommandResponse:
        """Get list of available camera controls."""
        return await self._cmd(Cmd.GET_CONTROLS)

    async def get_gain_segment(self) -> CommandResponse:
        """Get gain segment info."""
        return await self._cmd(Cmd.GET_GAIN_SEGMENT)

    async def save_image(self) -> CommandResponse:
        """Save the current image."""
        return await self._cmd(Cmd.SAVE_IMAGE)

    async def save_stack(self) -> CommandResponse:
        """Save the current stacked image."""
        return await self._cmd(Cmd.SAVE_STACK)


# ── Focuser ────────────────────────────────────────────────────────


class FocuserCommands(_Subsystem):
    """Focuser control commands."""

    async def open(self) -> CommandResponse:
        """Open the focuser."""
        return await self._cmd(Cmd.OPEN_FOCUSER)

    async def close(self) -> CommandResponse:
        """Close the focuser."""
        return await self._cmd(Cmd.CLOSE_FOCUSER)

    async def move(self, step: int, ret_step: bool = True) -> CommandResponse:
        """Move focuser by N steps.

        Args:
            step: Number of steps (positive = outward, negative = inward).
            ret_step: Whether to return the actual step in the response.
        """
        return await self._cmd(Cmd.MOVE_FOCUSER, {"step": step, "ret_step": ret_step})

    async def stop(self) -> CommandResponse:
        """Stop focuser movement."""
        return await self._cmd(Cmd.STOP_FOCUSER)

    async def start_auto_focus(self) -> CommandResponse:
        """Start autofocus."""
        return await self._cmd(Cmd.START_AUTO_FOCUS)

    async def stop_auto_focus(self) -> CommandResponse:
        """Stop autofocus."""
        return await self._cmd(Cmd.STOP_AUTO_FOCUS)

    async def get_position(self) -> CommandResponse:
        """Get current focuser position."""
        return await self._cmd(Cmd.GET_FOCUSER_POSITION)

    async def get_state(self) -> CommandResponse:
        """Get focuser state."""
        return await self._cmd(Cmd.GET_FOCUSER_STATE)

    async def get_setting(self) -> CommandResponse:
        """Get focuser settings."""
        return await self._cmd(Cmd.GET_FOCUSER_SETTING)

    async def set_setting(self, **params: Any) -> CommandResponse:
        """Set focuser settings."""
        return await self._cmd(Cmd.SET_FOCUSER_SETTING, params)

    async def reset_factory_position(self) -> CommandResponse:
        """Reset focuser to factory position."""
        return await self._cmd(Cmd.RESET_FACTORY_FOCAL_POS)


# ── Filter Wheel ───────────────────────────────────────────────────


class WheelCommands(_Subsystem):
    """Filter wheel control commands."""

    async def open(self) -> CommandResponse:
        """Open the filter wheel."""
        return await self._cmd(Cmd.OPEN_WHEEL)

    async def close(self) -> CommandResponse:
        """Close the filter wheel."""
        return await self._cmd(Cmd.CLOSE_WHEEL)

    async def get_position(self) -> CommandResponse:
        """Get current filter wheel position."""
        return await self._cmd(Cmd.GET_WHEEL_POSITION)

    async def set_position(self, position: int) -> CommandResponse:
        """Set filter wheel position."""
        return await self._cmd(Cmd.SET_WHEEL_POSITION, {"position": position})

    async def get_state(self) -> CommandResponse:
        """Get filter wheel state."""
        return await self._cmd(Cmd.GET_WHEEL_STATE)

    async def calibrate(self) -> CommandResponse:
        """Calibrate the filter wheel."""
        return await self._cmd(Cmd.CALIBRATE_WHEEL)

    async def get_slot_names(self) -> CommandResponse:
        """Get filter slot names."""
        return await self._cmd(Cmd.GET_WHEEL_SLOT_NAME)

    async def set_slot_names(self, names: list[str]) -> CommandResponse:
        """Set filter slot names."""
        return await self._cmd(Cmd.SET_WHEEL_SLOT_NAME, {"names": names})


# ── View / Preview ─────────────────────────────────────────────────


class ViewCommands(_Subsystem):
    """View/preview mode commands."""

    async def start(
        self,
        mode: str = "star",
        target_name: str = "",
        target_ra_dec: list[float] | None = None,
        lp_filter: bool = False,
    ) -> CommandResponse:
        """Start preview/view mode.

        Args:
            mode: View mode ("star", "moon", "sun", "scenery", etc.).
            target_name: Name of the target.
            target_ra_dec: [RA/15, Dec] coordinates.
            lp_filter: Enable light pollution filter.
        """
        params: dict[str, Any] = {"mode": mode}
        if target_name:
            params["target_name"] = target_name
        if target_ra_dec is not None:
            params["target_ra_dec"] = target_ra_dec
        if lp_filter:
            params["lp_filter"] = lp_filter
        return await self._cmd(Cmd.START_VIEW, params)

    async def stop(self, stage: str | None = None) -> CommandResponse:
        """Stop view mode."""
        params: dict[str, Any] = {}
        if stage is not None:
            params["stage"] = stage
        return await self._cmd(Cmd.STOP_VIEW, params or None)

    async def cancel(self) -> CommandResponse:
        """Cancel the current view."""
        return await self._cmd(Cmd.CANCEL_VIEW)

    async def get_state(self) -> CommandResponse:
        """Get current view state."""
        return await self._cmd(Cmd.GET_VIEW_STATE)


# ── Stacking ───────────────────────────────────────────────────────


class StackCommands(_Subsystem):
    """Stacking commands."""

    async def start(self, restart: bool = False) -> CommandResponse:
        """Start stacking.

        Args:
            restart: Whether to restart stacking from scratch.
        """
        return await self._cmd(Cmd.START_STACK, {"restart": restart})

    async def start_batch(self) -> CommandResponse:
        """Start batch stacking."""
        return await self._cmd(Cmd.START_BATCH_STACK)

    async def stop_batch(self) -> CommandResponse:
        """Stop batch stacking."""
        return await self._cmd(Cmd.STOP_BATCH_STACK)

    async def clear_batch(self) -> CommandResponse:
        """Clear batch stacking data."""
        return await self._cmd(Cmd.CLEAR_BATCH_STACK)

    async def start_planet(self, file: str, mode: str = "") -> CommandResponse:
        """Start planet stacking."""
        return await self._cmd(Cmd.START_PLANET_STACK, {"file": file, "mode": mode})

    async def stop_planet(self) -> CommandResponse:
        """Stop planet stacking."""
        return await self._cmd(Cmd.STOP_PLANET_STACK)

    async def clear(self) -> CommandResponse:
        """Clear stacking data."""
        return await self._cmd(Cmd.CLEAR_STACK)

    async def is_stacked(self) -> bool:
        """Check if stacking is active."""
        resp = await self._cmd(Cmd.IS_STACKED)
        return bool(resp.result)

    async def get_info(self) -> CommandResponse:
        """Get stack info."""
        return await self._cmd(Cmd.GET_STACK_INFO)

    async def get_setting(self) -> CommandResponse:
        """Get stack settings."""
        return await self._cmd(Cmd.GET_STACK_SETTING)

    async def set_setting(self, **params: Any) -> CommandResponse:
        """Set stack settings."""
        return await self._cmd(Cmd.SET_STACK_SETTING, params)

    async def get_stacked_img(self) -> CommandResponse:
        """Get the current stacked image."""
        return await self._cmd(Cmd.GET_STACKED_IMG)


# ── Plate Solving ──────────────────────────────────────────────────


class SolveCommands(_Subsystem):
    """Plate solving commands."""

    async def start(self) -> CommandResponse:
        """Start plate solving."""
        return await self._cmd(Cmd.START_SOLVE)

    async def stop(self) -> CommandResponse:
        """Stop plate solving."""
        return await self._cmd(Cmd.STOP_SOLVE)

    async def get_result(self) -> SolveResult:
        """Get plate solve result."""
        resp = await self._cmd(Cmd.GET_SOLVE_RESULT)
        r = resp.result or {}
        return SolveResult.model_validate(r)

    async def get_last_result(self) -> SolveResult:
        """Get last plate solve result."""
        resp = await self._cmd(Cmd.GET_LAST_SOLVE_RESULT)
        r = resp.result or {}
        return SolveResult.model_validate(r)


# ── Image Management ───────────────────────────────────────────────


class ImageCommands(_Subsystem):
    """Image file management commands."""

    async def get_files(self) -> CommandResponse:
        """Get list of image files."""
        return await self._cmd(Cmd.GET_IMG_FILE)

    async def get_file_info(self, name: str) -> CommandResponse:
        """Get info about a specific image file."""
        return await self._cmd(Cmd.GET_IMG_FILE_INFO, {"name": name})

    async def get_thumbnail(self, name: str) -> CommandResponse:
        """Get thumbnail for an image file."""
        return await self._cmd(Cmd.GET_IMG_THUMBNAIL, {"name": name})

    async def delete(self, name: str) -> CommandResponse:
        """Delete an image file."""
        return await self._cmd(Cmd.DELETE_IMAGE, {"name": name})

    async def delete_all(self) -> CommandResponse:
        """Delete all image files."""
        return await self._cmd(Cmd.DELETE_ALL_IMAGE)

    async def get_current(self) -> CommandResponse:
        """Get the current live image."""
        return await self._cmd(Cmd.GET_CURRENT_IMG)

    async def start_annotate(self) -> CommandResponse:
        """Start annotation of the current image."""
        return await self._cmd(Cmd.START_ANNOTATE)

    async def stop_annotate(self) -> CommandResponse:
        """Stop annotation."""
        return await self._cmd(Cmd.STOP_ANNOTATE)

    async def start_ai_process(self) -> CommandResponse:
        """Start AI processing on the current image."""
        return await self._cmd(Cmd.START_AI_PROCESS)

    async def get_albums(self) -> CommandResponse:
        """Get list of albums."""
        return await self._cmd(Cmd.GET_ALBUMS)

    async def set_favorite(self, name: str, favorite: bool) -> CommandResponse:
        """Mark/unmark an image as favorite."""
        return await self._cmd(Cmd.SET_IS_FAVORITE, {"name": name, "is_favorite": favorite})


# ── Streaming ──────────────────────────────────────────────────────


class StreamCommands(_Subsystem):
    """Video/image streaming commands."""

    async def start(self) -> CommandResponse:
        """Start image streaming."""
        return await self._cmd(Cmd.BEGIN_STREAMING)

    async def stop(self) -> CommandResponse:
        """Stop image streaming."""
        return await self._cmd(Cmd.STOP_STREAMING)

    async def start_record_avi(self) -> CommandResponse:
        """Start AVI recording."""
        return await self._cmd(Cmd.START_RECORD_AVI)

    async def stop_record_avi(self) -> CommandResponse:
        """Stop AVI recording."""
        return await self._cmd(Cmd.STOP_RECORD_AVI)

    async def get_rtmp_config(self) -> CommandResponse:
        """Get RTMP streaming configuration."""
        return await self._cmd(Cmd.GET_RTMP_CONFIG)

    async def set_rtmp_config(self, **params: Any) -> CommandResponse:
        """Set RTMP streaming configuration."""
        return await self._cmd(Cmd.SET_RTMP_CONFIG, params)


# ── Polar Alignment ────────────────────────────────────────────────


class PolarAlignCommands(_Subsystem):
    """Polar alignment commands."""

    async def start(self) -> CommandResponse:
        """Start polar alignment procedure."""
        return await self._cmd(Cmd.START_POLAR_ALIGN)

    async def stop(self) -> CommandResponse:
        """Stop polar alignment."""
        return await self._cmd(Cmd.STOP_POLAR_ALIGN)

    async def pause(self) -> CommandResponse:
        """Pause polar alignment."""
        return await self._cmd(Cmd.PAUSE_POLAR_ALIGN)

    async def clear(self) -> CommandResponse:
        """Clear polar alignment data."""
        return await self._cmd(Cmd.CLEAR_POLAR_ALIGN)

    async def check_alt(self) -> CommandResponse:
        """Check polar alignment altitude."""
        return await self._cmd(Cmd.CHECK_PA_ALT)

    async def get_polar_axis(self) -> CommandResponse:
        """Get polar axis info."""
        return await self._cmd(Cmd.GET_POLAR_AXIS)


# ── System ─────────────────────────────────────────────────────────


class SystemCommands(_Subsystem):
    """System and network commands."""

    async def get_device_state(self) -> DeviceState:
        """Get complete device state."""
        return await self._client.get_device_state()

    async def get_setting(self) -> CommandResponse:
        """Get device settings."""
        return await self._cmd(Cmd.GET_SETTING)

    async def set_setting(self, **params: Any) -> CommandResponse:
        """Set device settings."""
        return await self._cmd(Cmd.SET_SETTING, params)

    async def shutdown(self) -> CommandResponse:
        """Shut down the device."""
        return await self._cmd(Cmd.PI_SHUTDOWN)

    async def reboot(self) -> CommandResponse:
        """Reboot the device."""
        return await self._cmd(Cmd.PI_REBOOT)

    async def get_pi_info(self) -> CommandResponse:
        """Get system info."""
        return await self._cmd(Cmd.PI_GET_INFO)

    async def get_time(self) -> CommandResponse:
        """Get device time."""
        return await self._cmd(Cmd.PI_GET_TIME)

    async def set_time(self, timestamp: int) -> CommandResponse:
        """Set device time."""
        return await self._cmd(Cmd.PI_SET_TIME, {"timestamp": timestamp})

    async def get_disk_volume(self) -> CommandResponse:
        """Get disk/storage volume info."""
        return await self._cmd(Cmd.GET_DISK_VOLUME)

    async def play_sound(self, sound: str) -> CommandResponse:
        """Play a sound on the device."""
        return await self._cmd(Cmd.PLAY_SOUND, {"sound": sound})

    async def get_ap(self) -> CommandResponse:
        """Get WiFi AP settings."""
        return await self._cmd(Cmd.PI_GET_AP)

    async def set_ap(self, ssid: str, passwd: str, is_5g: bool = False) -> CommandResponse:
        """Set WiFi AP settings."""
        return await self._cmd(Cmd.PI_SET_AP, {"ssid": ssid, "passwd": passwd, "is_5g": is_5g})

    async def station_scan(self) -> CommandResponse:
        """Scan for WiFi networks."""
        return await self._cmd(Cmd.PI_STATION_SCAN)

    async def station_list(self) -> CommandResponse:
        """List saved WiFi networks."""
        return await self._cmd(Cmd.PI_STATION_LIST)

    async def station_connect(self, ssid: str, passwd: str = "") -> CommandResponse:
        """Connect to a WiFi network."""
        return await self._cmd(Cmd.PI_STATION_SELECT, {"ssid": ssid, "passwd": passwd})

    async def station_state(self) -> CommandResponse:
        """Get WiFi station connection state."""
        return await self._cmd(Cmd.PI_STATION_STATE)

    async def check_internet(self) -> CommandResponse:
        """Check internet connectivity."""
        return await self._cmd(Cmd.CHECK_INTERNET)

    async def scope_get_test_date(self) -> CommandResponse:
        """Get mount controller test/diagnostic date (3.1.2+)."""
        return await self._cmd(Cmd.SCOPE_GET_TEST_DATE)


# ── Planning ───────────────────────────────────────────────────────


class PlanCommands(_Subsystem):
    """Observation planning commands."""

    async def list_plans(self) -> CommandResponse:
        """List available plans."""
        return await self._cmd(Cmd.LIST_PLAN)

    async def get_plan(self, name: str) -> CommandResponse:
        """Get a specific plan."""
        return await self._cmd(Cmd.GET_PLAN, {"name": name})

    async def set_plan(self, **params: Any) -> CommandResponse:
        """Set/create a plan."""
        return await self._cmd(Cmd.SET_PLAN, params)

    async def delete_plan(self, name: str) -> CommandResponse:
        """Delete a plan."""
        return await self._cmd(Cmd.DELETE_PLAN, {"name": name})

    async def import_plan(self, **params: Any) -> CommandResponse:
        """Import a plan."""
        return await self._cmd(Cmd.IMPORT_PLAN, params)

    async def get_enabled_plan(self) -> CommandResponse:
        """Get the currently enabled plan."""
        return await self._cmd(Cmd.GET_ENABLED_PLAN)


# ── Compass / Sensors ──────────────────────────────────────────────


class SensorCommands(_Subsystem):
    """Compass and sensor calibration commands."""

    async def start_compass_calibration(self) -> CommandResponse:
        """Start compass calibration."""
        return await self._cmd(Cmd.START_COMPASS_CALIBRATION)

    async def stop_compass_calibration(self) -> CommandResponse:
        """Stop compass calibration."""
        return await self._cmd(Cmd.STOP_COMPASS_CALIBRATION)

    async def get_compass_state(self) -> CommandResponse:
        """Get compass state."""
        return await self._cmd(Cmd.GET_COMPASS_STATE)

    async def start_gsensor_calibration(self) -> CommandResponse:
        """Start G-sensor (accelerometer) calibration."""
        return await self._cmd(Cmd.START_GSENSOR_CALIBRATION)


# ── Photometry ─────────────────────────────────────────────────────


class PhotometryCommands(_Subsystem):
    """Photometry commands (full set available in firmware 3.1.2+/7.32+)."""

    async def check(self) -> CommandResponse:
        """Start a photometry check."""
        return await self._cmd(Cmd.CHECK_PHOTOMETRY)

    async def get_result(self) -> CommandResponse:
        """Get photometry check result."""
        return await self._cmd(Cmd.GET_PHOTOMETRY_RESULT)

    async def get_stars(self) -> CommandResponse:
        """Get photometry star list (3.1.2+)."""
        return await self._cmd(Cmd.GET_PHOTOMETRY_STARS)

    async def get_plot(self) -> CommandResponse:
        """Get photometry plot data (3.1.2+)."""
        return await self._cmd(Cmd.GET_PHOTOMETRY_PLOT)

    async def set_config(self, **params: Any) -> CommandResponse:
        """Set photometry configuration (3.1.2+)."""
        return await self._cmd(Cmd.SET_PHOTOMETRY, params)


def attach_subsystems(client: SeestarClient) -> None:
    """Attach all command subsystems to a client instance."""
    client.mount = MountCommands(client)
    client.camera = CameraCommands(client)
    client.focuser = FocuserCommands(client)
    client.wheel = WheelCommands(client)
    client.view = ViewCommands(client)
    client.stack = StackCommands(client)
    client.solve = SolveCommands(client)
    client.image = ImageCommands(client)
    client.stream = StreamCommands(client)
    client.polar_align = PolarAlignCommands(client)
    client.system = SystemCommands(client)
    client.plan = PlanCommands(client)
    client.sensor = SensorCommands(client)
    client.photometry = PhotometryCommands(client)
