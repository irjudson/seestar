"""
Generate markdown reports from extracted VersionData.
"""

from pathlib import Path
from .extract import VersionData, load


def render_version_report(data: VersionData) -> str:
    lines = []
    a = lines.append

    a(f"# Seestar App v{data.version} — Analysis Report\n")

    # Version info
    a("## Version Info\n")
    a(f"| Field | Value |")
    a(f"|-------|-------|")
    a(f"| App version | `{data.version}` |")
    if data.info.firmware_version:
        a(f"| Target firmware (32-bit) | `{data.info.firmware_version}` |")
    if data.info.firmware_version_64:
        a(f"| Target firmware (64-bit) | `{data.info.firmware_version_64}` |")
    if data.info.fw_need_update_version:
        a(f"| Pushes device to firmware | `{data.info.fw_need_update_version}` |")
    if data.info.fw_force_upgrade_below:
        a(f"| Force upgrade below firmware | `{data.info.fw_force_upgrade_below}` |")
    if data.info.api_base_url:
        a(f"| API base URL | `{data.info.api_base_url}` |")
    if data.info.api_astro_url:
        a(f"| API astro URL | `{data.info.api_astro_url}` |")
    if data.update_mechanism:
        a(f"| Update mechanism | `{data.update_mechanism}` |")
    a("")

    # Commands
    a(f"## Socket Commands ({len(data.commands)})\n")
    if data.commands:
        a("| Method | Class | Params |")
        a("|--------|-------|--------|")
        for cmd in sorted(data.commands, key=lambda c: c.method):
            params = ", ".join(f"`{p}`" for p in cmd.params) if cmd.params else "—"
            a(f"| `{cmd.method}` | {cmd.name} | {params} |")
    else:
        a("_No commands extracted._")
    a("")

    # API endpoints
    a(f"## API Endpoints ({len(data.endpoints)})\n")
    if data.endpoints:
        a("| Method | Path | Function |")
        a("|--------|------|----------|")
        for ep in data.endpoints:
            a(f"| `{ep.method}` | `{ep.path}` | {ep.description} |")
    else:
        a("_No endpoints extracted._")
    a("")

    # BLE
    a("## BLE Protocol\n")
    ble = data.ble
    if ble.service_uuid:
        a(f"| Field | Value |")
        a(f"|-------|-------|")
        a(f"| Service UUID | `{ble.service_uuid}` |")
        if ble.write_char_uuid:
            a(f"| Write/Notify characteristic | `{ble.write_char_uuid}` |")
        if ble.read_char_uuid:
            a(f"| Read characteristic | `{ble.read_char_uuid}` |")
        if ble.mtu:
            a(f"| MTU | `{ble.mtu}` |")
        if ble.protocol_methods:
            a(f"| Protocol methods | {', '.join(f'`{m}`' for m in ble.protocol_methods)} |")
    else:
        a("_No BLE info extracted._")
    a("")

    # Public key fingerprint
    if data.info.pub_key:
        a("## Signing Key\n")
        a(f"```\n{data.info.pub_key[:64]}...\n```\n")

    return "\n".join(lines)


def render_comparison(v1: VersionData, v2: VersionData) -> str:
    lines = []
    a = lines.append

    a(f"# Seestar v{v1.version} → v{v2.version} Comparison\n")

    # Firmware version changes
    a("## Version Mapping Changes\n")
    a(f"| Field | v{v1.version} | v{v2.version} |")
    a(f"|-------|{'—' * (len(v1.version)+2)}|{'—' * (len(v2.version)+2)}|")
    fields = [
        ("firmware_version", "Target firmware (32-bit)"),
        ("firmware_version_64", "Target firmware (64-bit)"),
        ("fw_need_update_version", "Pushes device to"),
        ("fw_force_upgrade_below", "Force upgrade below"),
        ("api_base_url", "API base URL"),
        ("update_mechanism", "Update mechanism"),
    ]
    for attr, label in fields:
        val1 = getattr(v1.info, attr, "") or getattr(v1, attr, "")
        val2 = getattr(v2.info, attr, "") or getattr(v2, attr, "")
        changed = " ⚠️" if val1 != val2 else ""
        a(f"| {label}{changed} | `{val1 or '—'}` | `{val2 or '—'}` |")
    a("")

    # Commands diff
    cmds1 = {c.method: c for c in v1.commands}
    cmds2 = {c.method: c for c in v2.commands}
    added = sorted(set(cmds2) - set(cmds1))
    removed = sorted(set(cmds1) - set(cmds2))
    changed = sorted(
        m for m in set(cmds1) & set(cmds2)
        if cmds1[m].params != cmds2[m].params
    )

    a(f"## Socket Commands\n")
    a(f"- Total v{v1.version}: **{len(cmds1)}** commands")
    a(f"- Total v{v2.version}: **{len(cmds2)}** commands")
    a(f"- Added: **{len(added)}**, Removed: **{len(removed)}**, Changed params: **{len(changed)}**\n")

    if added:
        a("### Added Commands\n")
        a("| Method | Params |")
        a("|--------|--------|")
        for m in added:
            c = cmds2[m]
            params = ", ".join(f"`{p}`" for p in c.params) if c.params else "—"
            a(f"| `{m}` | {params} |")
        a("")

    if removed:
        a("### Removed Commands\n")
        a("| Method |")
        a("|--------|")
        for m in removed:
            a(f"| `{m}` |")
        a("")

    if changed:
        a("### Changed Command Params\n")
        a("| Method | Before | After |")
        a("|--------|--------|-------|")
        for m in changed:
            before = ", ".join(f"`{p}`" for p in cmds1[m].params) or "—"
            after = ", ".join(f"`{p}`" for p in cmds2[m].params) or "—"
            a(f"| `{m}` | {before} | {after} |")
        a("")

    # API endpoints diff
    eps1 = {f"{e.method}:{e.path}" for e in v1.endpoints}
    eps2 = {f"{e.method}:{e.path}" for e in v2.endpoints}
    ep_added = sorted(eps2 - eps1)
    ep_removed = sorted(eps1 - eps2)

    a(f"## API Endpoints\n")
    a(f"- Total v{v1.version}: **{len(eps1)}**, v{v2.version}: **{len(eps2)}**")
    a(f"- Added: **{len(ep_added)}**, Removed: **{len(ep_removed)}**\n")

    if ep_added:
        a("### Added Endpoints\n")
        for e in ep_added:
            a(f"- `{e}`")
        a("")

    if ep_removed:
        a("### Removed Endpoints\n")
        for e in ep_removed:
            a(f"- `{e}`")
        a("")

    # BLE changes
    ble1, ble2 = v1.ble, v2.ble
    ble_changed = any([
        ble1.service_uuid != ble2.service_uuid,
        ble1.write_char_uuid != ble2.write_char_uuid,
        ble1.mtu != ble2.mtu,
        set(ble1.protocol_methods) != set(ble2.protocol_methods),
    ])
    if ble_changed:
        a("## BLE Changes ⚠️\n")
        if ble1.service_uuid != ble2.service_uuid:
            a(f"- Service UUID: `{ble1.service_uuid}` → `{ble2.service_uuid}`")
        if ble1.mtu != ble2.mtu:
            a(f"- MTU: `{ble1.mtu}` → `{ble2.mtu}`")
        new_methods = set(ble2.protocol_methods) - set(ble1.protocol_methods)
        removed_methods = set(ble1.protocol_methods) - set(ble2.protocol_methods)
        if new_methods:
            a(f"- New BLE methods: {', '.join(f'`{m}`' for m in sorted(new_methods))}")
        if removed_methods:
            a(f"- Removed BLE methods: {', '.join(f'`{m}`' for m in sorted(removed_methods))}")
        a("")
    else:
        a("## BLE\n\nNo changes detected.\n")

    return "\n".join(lines)


def save_report(content: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  Report: {path}")
