# seestar

Python client library for ZWO Seestar smart telescopes. Reverse-engineered from the Android app v3.0.2 and the on-device ASCOM Alpaca server.

## Install

```bash
pip install -e .
```

## Quick Start

```python
import asyncio
import seestar

SEESTAR_HOST = "192.168.x.x"  # your device IP

async def main():
    # Or discover devices on the network
    devices = await seestar.discover(timeout=5.0)
    host = devices[0].host if devices else SEESTAR_HOST

    # Connect and control
    async with seestar.SeestarClient(host) as client:
        state = await client.get_device_state()
        print(f"{state.device.name} - FW {state.device.firmware_ver_string}")
        print(f"Battery: {state.pi_status.battery_capacity}%")

        coord = await client.mount.get_equ_coord()
        print(f"RA: {coord.ra:.4f}h  Dec: {coord.dec:.4f}°")

        # Goto a target and stack
        await client.view.start(mode="star", target_name="M42",
                                target_ra_dec=[5.588 / 15, -5.39])
        await client.stack.start(restart=True)

asyncio.run(main())
```

## Command Subsystems

All commands are organized into subsystems on the client:

| Subsystem | Access | Examples |
|-----------|--------|----------|
| Mount | `client.mount` | `get_equ_coord()`, `goto()`, `park()`, `speed_move()` |
| Camera | `client.camera` | `start_exposure()`, `set_control_value()`, `save_image()` |
| Focuser | `client.focuser` | `move()`, `start_auto_focus()`, `get_position()` |
| Filter Wheel | `client.wheel` | `set_position()`, `calibrate()`, `get_slot_names()` |
| View | `client.view` | `start()`, `stop()`, `get_state()` |
| Stacking | `client.stack` | `start()`, `start_batch()`, `get_stacked_img()` |
| Plate Solve | `client.solve` | `start()`, `get_result()` |
| Images | `client.image` | `get_files()`, `get_thumbnail()`, `start_annotate()` |
| Streaming | `client.stream` | `start()`, `stop()`, `start_record_avi()` |
| Polar Align | `client.polar_align` | `start()`, `stop()`, `get_polar_axis()` |
| System | `client.system` | `get_setting()`, `shutdown()`, `station_scan()` |
| Planning | `client.plan` | `list_plans()`, `set_plan()`, `import_plan()` |
| Sensors | `client.sensor` | `start_compass_calibration()`, `get_compass_state()` |

## Events

```python
async with seestar.SeestarClient(host) as client:
    client.events.on("AutoGoto", lambda e: print(f"Goto: {e.state}"))
    client.events.on("Stack", lambda e: print(f"Stack: {e.state}"))
    client.events.on_category(seestar.EventCategory.DEVICE_STATE, handler)
    client.events.on_all(lambda e: print(f"[{e.Event}] {e.state}"))
```

## ASCOM Alpaca

The Seestar also runs an ASCOM Alpaca REST server. Use it as an alternative:

```python
async with seestar.AlpacaClient(host) as alpaca:
    telescope = alpaca.telescope()
    ra = await telescope.get_ra()
    await telescope.slew_to_coordinates_async(ra=5.588, dec=-5.39)
```

## Protocol

Communication is line-delimited JSON over TCP port 4700 with `\r\n` terminators. Connection requires an RSA handshake, followed by a heartbeat every 4 seconds. See [docs/seestar-api-reference.md](docs/seestar-api-reference.md) for the full protocol specification covering 150+ commands, 33 event types, and the complete device state model.

| Port | Purpose |
|------|---------|
| 4700 | Command/response (JSON over TCP) |
| 4720 | UDP discovery broadcast |
| 4800 | Live image stream (telephoto) |
| 4804 | Live image stream (wide-angle) |
| 4554/4555 | RTMP video streams |
| 4801 | File transfer |
| 80 | ASCOM Alpaca REST API |
