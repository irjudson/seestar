"""Tests for Pydantic models."""

from seestar.models import (
    CommandRequest,
    CommandResponse,
    DeviceState,
    DiscoveryResult,
    EquatorialCoord,
    EventMessage,
    SeestarDevice,
    SeestarPiStatus,
    SeestarSetting,
    ViewData,
)


def test_command_request_basic():
    req = CommandRequest(id=1, method="test_connection")
    assert req.id == 1
    assert req.method == "test_connection"
    assert req.params is None


def test_command_request_with_params():
    req = CommandRequest(id=2, method="set_setting", params={"dark_mode": True})
    data = req.model_dump(exclude_none=True)
    assert data["params"] == {"dark_mode": True}


def test_command_response():
    resp = CommandResponse.model_validate({
        "id": 1,
        "method": "scope_get_equ_coord",
        "code": 0,
        "result": {"ra": 12.5, "dec": -30.2},
    })
    assert resp.code == 0
    assert resp.result["ra"] == 12.5


def test_command_response_error():
    resp = CommandResponse.model_validate({"id": 1, "code": 103})
    assert resp.code == 103


def test_event_message():
    msg = EventMessage.model_validate({
        "Event": "AutoGoto",
        "state": "working",
        "progress": 50,
    })
    assert msg.Event == "AutoGoto"
    assert msg.state == "working"


def test_discovery_result():
    result = DiscoveryResult.model_validate({
        "ssid": "Seestar_ABC123",
        "sn": "ABC123",
        "model": "Seestar",
        "is_verified": True,
        "product_model": "Seestar S50",
        "tcp_client_num": 1,
    })
    assert result.sn == "ABC123"
    assert result.product_model == "Seestar S50"


def test_device_state_nested():
    state = DeviceState.model_validate({
        "device": {
            "name": "Seestar",
            "sn": "TEST123",
            "firmware_ver_int": 2670,
            "firmware_ver_string": "6.70",
        },
        "mount": {"tracking": True, "equ_mode": False},
        "pi_status": {"temp": 45.0, "battery_capacity": 80},
    })
    assert state.device is not None
    assert state.device.sn == "TEST123"
    assert state.device.firmware_ver_int == 2670
    assert state.mount is not None
    assert state.mount.tracking is True
    assert state.pi_status is not None
    assert state.pi_status.battery_capacity == 80


def test_device_state_empty():
    state = DeviceState.model_validate({})
    assert state.device is None
    assert state.mount is None


def test_seestar_device_extra_fields():
    dev = SeestarDevice.model_validate({
        "name": "Test",
        "sn": "SN123",
        "unknown_field": "value",
    })
    assert dev.name == "Test"


def test_pi_status():
    status = SeestarPiStatus.model_validate({
        "temp": 52.3,
        "is_overtemp": False,
        "battery_capacity": 95,
        "charge_online": True,
    })
    assert status.temp == 52.3
    assert status.battery_capacity == 95


def test_setting():
    setting = SeestarSetting.model_validate({
        "expert_mode": True,
        "dark_mode": False,
        "isp_exp_ms": 1000.0,
        "stack_after_goto": True,
    })
    assert setting.expert_mode is True
    assert setting.isp_exp_ms == 1000.0


def test_equatorial_coord():
    coord = EquatorialCoord(ra=12.5, dec=-30.2)
    assert coord.ra == 12.5
    assert coord.dec == -30.2


def test_view_data():
    view = ViewData.model_validate({
        "state": "working",
        "mode": "star",
        "target_name": "M42",
        "target_ra_dec": [5.588, -5.39],
        "AutoGoto": {"state": "complete"},
    })
    assert view.target_name == "M42"
    assert view.AutoGoto is not None
    assert view.AutoGoto.state == "complete"


def test_view_data_3ppa():
    view = ViewData.model_validate({
        "state": "working",
        "mode": "pa",
        "3PPA": {"state": "step1"},
    })
    assert view.three_ppa is not None
    assert view.three_ppa.state == "step1"
