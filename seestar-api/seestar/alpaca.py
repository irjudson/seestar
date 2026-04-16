"""ASCOM Alpaca REST client for Seestar.

The Seestar runs an ASCOM Alpaca server on-device that bridges
standard ASCOM interfaces to the native socket protocol.

This module wraps the standard Alpaca REST API using httpx.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default Alpaca server port on Seestar devices
ALPACA_PORT = 80

# ASCOM device types available on Seestar
DEVICE_TYPES = [
    "telescope",
    "camera",
    "focuser",
    "filterwheel",
    "rotator",
    "covercalibrator",
    "switch",
    "dome",
    "safetymonitor",
    "observingconditions",
]


class AlpacaDevice:
    """Base class for an ASCOM Alpaca device."""

    def __init__(
        self,
        client: AlpacaClient,
        device_type: str,
        device_number: int = 0,
    ) -> None:
        self._client = client
        self._device_type = device_type
        self._device_number = device_number
        self._client_id = 1
        self._tx_id = 1

    def _next_tx(self) -> int:
        tx = self._tx_id
        self._tx_id += 1
        return tx

    async def get(self, property_name: str, **params: Any) -> Any:
        """GET a device property."""
        return await self._client.get_property(
            self._device_type, self._device_number, property_name,
            ClientID=self._client_id, ClientTransactionID=self._next_tx(),
            **params,
        )

    async def put(self, method_name: str, **params: Any) -> Any:
        """PUT (invoke) a device method."""
        return await self._client.put_method(
            self._device_type, self._device_number, method_name,
            ClientID=self._client_id, ClientTransactionID=self._next_tx(),
            **params,
        )


class AlpacaTelescope(AlpacaDevice):
    """ASCOM Alpaca Telescope device."""

    def __init__(self, client: AlpacaClient, device_number: int = 0) -> None:
        super().__init__(client, "telescope", device_number)

    async def get_ra(self) -> float:
        return await self.get("rightascension")

    async def get_dec(self) -> float:
        return await self.get("declination")

    async def get_altitude(self) -> float:
        return await self.get("altitude")

    async def get_azimuth(self) -> float:
        return await self.get("azimuth")

    async def get_tracking(self) -> bool:
        return await self.get("tracking")

    async def set_tracking(self, value: bool) -> None:
        await self.put("tracking", Tracking=value)

    async def get_slewing(self) -> bool:
        return await self.get("slewing")

    async def get_at_park(self) -> bool:
        return await self.get("atpark")

    async def get_at_home(self) -> bool:
        return await self.get("athome")

    async def get_connected(self) -> bool:
        return await self.get("connected")

    async def set_connected(self, value: bool) -> None:
        await self.put("connected", Connected=value)

    async def slew_to_coordinates(self, ra: float, dec: float) -> None:
        await self.put("slewtocoordinates", RightAscension=ra, Declination=dec)

    async def slew_to_coordinates_async(self, ra: float, dec: float) -> None:
        await self.put("slewtocoordinatesasync", RightAscension=ra, Declination=dec)

    async def sync_to_coordinates(self, ra: float, dec: float) -> None:
        await self.put("synctocoordinates", RightAscension=ra, Declination=dec)

    async def abort_slew(self) -> None:
        await self.put("abortslew")

    async def park(self) -> None:
        await self.put("park")

    async def unpark(self) -> None:
        await self.put("unpark")

    async def find_home(self) -> None:
        await self.put("findhome")

    async def move_axis(self, axis: int, rate: float) -> None:
        await self.put("moveaxis", Axis=axis, Rate=rate)

    async def get_site_latitude(self) -> float:
        return await self.get("sitelatitude")

    async def get_site_longitude(self) -> float:
        return await self.get("sitelongitude")

    async def set_site_latitude(self, lat: float) -> None:
        await self.put("sitelatitude", SiteLatitude=lat)

    async def set_site_longitude(self, lon: float) -> None:
        await self.put("sitelongitude", SiteLongitude=lon)


class AlpacaCamera(AlpacaDevice):
    """ASCOM Alpaca Camera device."""

    def __init__(self, client: AlpacaClient, device_number: int = 0) -> None:
        super().__init__(client, "camera", device_number)

    async def get_connected(self) -> bool:
        return await self.get("connected")

    async def set_connected(self, value: bool) -> None:
        await self.put("connected", Connected=value)

    async def get_camera_state(self) -> int:
        return await self.get("camerastate")

    async def get_image_ready(self) -> bool:
        return await self.get("imageready")

    async def start_exposure(self, duration: float, light: bool = True) -> None:
        await self.put("startexposure", Duration=duration, Light=light)

    async def stop_exposure(self) -> None:
        await self.put("stopexposure")

    async def abort_exposure(self) -> None:
        await self.put("abortexposure")

    async def get_gain(self) -> int:
        return await self.get("gain")

    async def set_gain(self, value: int) -> None:
        await self.put("gain", Gain=value)

    async def get_bin_x(self) -> int:
        return await self.get("binx")

    async def get_bin_y(self) -> int:
        return await self.get("biny")

    async def set_bin_x(self, value: int) -> None:
        await self.put("binx", BinX=value)

    async def set_bin_y(self, value: int) -> None:
        await self.put("biny", BinY=value)

    async def get_sensor_type(self) -> int:
        return await self.get("sensortype")

    async def get_ccd_temperature(self) -> float:
        return await self.get("ccdtemperature")

    async def get_pixel_size_x(self) -> float:
        return await self.get("pixelsizex")

    async def get_pixel_size_y(self) -> float:
        return await self.get("pixelsizey")


class AlpacaFocuser(AlpacaDevice):
    """ASCOM Alpaca Focuser device."""

    def __init__(self, client: AlpacaClient, device_number: int = 0) -> None:
        super().__init__(client, "focuser", device_number)

    async def get_connected(self) -> bool:
        return await self.get("connected")

    async def set_connected(self, value: bool) -> None:
        await self.put("connected", Connected=value)

    async def get_position(self) -> int:
        return await self.get("position")

    async def get_is_moving(self) -> bool:
        return await self.get("ismoving")

    async def get_max_step(self) -> int:
        return await self.get("maxstep")

    async def move(self, position: int) -> None:
        await self.put("move", Position=position)

    async def halt(self) -> None:
        await self.put("halt")


class AlpacaFilterWheel(AlpacaDevice):
    """ASCOM Alpaca Filter Wheel device."""

    def __init__(self, client: AlpacaClient, device_number: int = 0) -> None:
        super().__init__(client, "filterwheel", device_number)

    async def get_connected(self) -> bool:
        return await self.get("connected")

    async def set_connected(self, value: bool) -> None:
        await self.put("connected", Connected=value)

    async def get_position(self) -> int:
        return await self.get("position")

    async def set_position(self, value: int) -> None:
        await self.put("position", Position=value)

    async def get_names(self) -> list[str]:
        return await self.get("names")


class AlpacaClient:
    """ASCOM Alpaca REST API client.

    Usage::

        alpaca = AlpacaClient("<device-ip>")
        telescope = alpaca.telescope()

        ra = await telescope.get_ra()
        dec = await telescope.get_dec()

        await alpaca.close()
    """

    def __init__(
        self,
        host: str,
        port: int = ALPACA_PORT,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = f"http://{host}:{port}"
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> AlpacaClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ── Device factories ───────────────────────────────────────────

    def telescope(self, device_number: int = 0) -> AlpacaTelescope:
        return AlpacaTelescope(self, device_number)

    def camera(self, device_number: int = 0) -> AlpacaCamera:
        return AlpacaCamera(self, device_number)

    def focuser(self, device_number: int = 0) -> AlpacaFocuser:
        return AlpacaFocuser(self, device_number)

    def filter_wheel(self, device_number: int = 0) -> AlpacaFilterWheel:
        return AlpacaFilterWheel(self, device_number)

    # ── Raw API access ─────────────────────────────────────────────

    async def get_property(
        self, device_type: str, device_number: int, property_name: str, **params: Any
    ) -> Any:
        """GET a device property.

        Returns the 'Value' field from the Alpaca response.
        """
        url = f"/api/v1/{device_type}/{device_number}/{property_name}"
        resp = await self._http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        error_number = data.get("ErrorNumber", 0)
        if error_number != 0:
            raise AlpacaError(error_number, data.get("ErrorMessage", "Unknown error"))
        return data.get("Value")

    async def put_method(
        self, device_type: str, device_number: int, method_name: str, **params: Any
    ) -> Any:
        """PUT (invoke) a device method.

        Returns the 'Value' field from the Alpaca response, if any.
        """
        url = f"/api/v1/{device_type}/{device_number}/{method_name}"
        resp = await self._http.put(url, data=params)
        resp.raise_for_status()
        data = resp.json()
        error_number = data.get("ErrorNumber", 0)
        if error_number != 0:
            raise AlpacaError(error_number, data.get("ErrorMessage", "Unknown error"))
        return data.get("Value")

    async def get_server_description(self) -> dict[str, Any]:
        """Get Alpaca server description."""
        resp = await self._http.get("/management/v1/description")
        resp.raise_for_status()
        return resp.json().get("Value", {})

    async def get_configured_devices(self) -> list[dict[str, Any]]:
        """Get list of configured ASCOM devices."""
        resp = await self._http.get("/management/v1/configureddevices")
        resp.raise_for_status()
        return resp.json().get("Value", [])


class AlpacaError(Exception):
    """ASCOM Alpaca API error."""

    def __init__(self, error_number: int, error_message: str) -> None:
        self.error_number = error_number
        self.error_message = error_message
        super().__init__(f"Alpaca error {error_number}: {error_message}")
