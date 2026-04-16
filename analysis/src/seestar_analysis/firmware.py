"""
Extract and analyze firmware packages (iscope_64) embedded in Seestar APKs.

Each APK/XAPK ships a bzip2-compressed tar archive at assets/iscope_64 (or
assets/iscope_64_arm64) containing:
  - update_package.sh       — the install/update orchestrator
  - deb-build/asiair_armhf/ — main ASIAIR software tree
  - others/                 — extra binaries + Seestar_X.X.X.bin (MCU firmware)
"""

import zipfile
import bz2
import tarfile
import io
import re
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
import json


@dataclass
class FirmwareInfo:
    apk_version: str
    asset_name: str = ""          # e.g. "iscope_64" or "iscope_64_arm64"
    mcu_firmware: str = ""        # e.g. "Seestar_2.1.4.bin"
    mcu_version: str = ""         # e.g. "2.1.4"
    asiair_deb_version: str = ""  # version from deb control file if present
    scripts: list[str] = field(default_factory=list)   # shell script names
    binaries: list[str] = field(default_factory=list)  # binary names
    all_files: list[str] = field(default_factory=list) # full file list
    network_sh_excerpt: str = ""
    bluetooth_sh_excerpt: str = ""
    update_sh_excerpt: str = ""
    notes: list[str] = field(default_factory=list)


def _find_asset(zf: zipfile.ZipFile) -> str | None:
    """Find the iscope firmware asset inside a ZipFile.
    Prefer 64-bit variants; fall back to 32-bit 'iscope' for older versions."""
    candidates = [
        "assets/iscope_64_arm64",
        "assets/iscope_64",
        "assets/iscope_64_armeabi_v7a",
        "assets/iscope",  # older versions (< 2.6.4) use 32-bit
    ]
    names = set(zf.namelist())
    for c in candidates:
        if c in names:
            return c
    # Fallback: any assets/iscope* entry (exact, not directories)
    for n in zf.namelist():
        if n.startswith("assets/iscope") and "/" not in n[len("assets/"):]:
            return n
    return None


def _open_apk(apk_path: Path) -> zipfile.ZipFile | None:
    try:
        return zipfile.ZipFile(apk_path, 'r')
    except Exception:
        return None


def _read_asset_bytes(apk_path: Path) -> tuple[bytes, str]:
    """
    Return (raw_bytes, asset_name) for the iscope_64 asset.
    Handles both plain .apk and split XAPK bundles.

    XAPK structure: a zip containing multiple APKs:
      - com.zwo.seestar.apk  — main APK (no firmware asset)
      - asset_pack_0.apk     — contains assets/iscope_64 etc.
      - config.*.apk         — density/ABI splits
    """
    with zipfile.ZipFile(apk_path, 'r') as outer:
        # Plain APK: asset directly inside
        asset = _find_asset(outer)
        if asset:
            return outer.read(asset), asset

        # XAPK: search ALL inner APKs for the asset
        apk_entries = [n for n in outer.namelist() if n.endswith('.apk')]
        for apk_name in apk_entries:
            try:
                inner_bytes = outer.read(apk_name)
                with zipfile.ZipFile(io.BytesIO(inner_bytes), 'r') as inner:
                    asset = _find_asset(inner)
                    if asset:
                        return inner.read(asset), asset
            except Exception:
                continue

    return b"", ""


def _extract_to_dir(raw: bytes, dest: Path) -> bool:
    """Decompress bzip2 + extract tar into dest."""
    dest.mkdir(parents=True, exist_ok=True)
    try:
        data = bz2.decompress(raw)
    except Exception:
        # Try treating as raw tar
        data = raw

    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(dest)
        return True
    except Exception as e:
        return False


def _slurp(path: Path, max_lines: int = 60) -> str:
    try:
        lines = path.read_text(errors='ignore').splitlines()
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""


def analyze_firmware(apk_version: str, apk_path: Path, work_dir: Path) -> FirmwareInfo:
    """Extract and analyze the iscope_64 firmware bundle from an APK."""
    info = FirmwareInfo(apk_version=apk_version)

    extract_dir = work_dir / f"fw_{apk_version}"

    # Use cached extraction if available
    if not extract_dir.exists() or not any(extract_dir.rglob("*")):
        raw, asset_name = _read_asset_bytes(apk_path)
        if not raw:
            info.notes.append("No iscope_64 asset found in APK")
            return info
        info.asset_name = asset_name.split('/')[-1]
        ok = _extract_to_dir(raw, extract_dir)
        if not ok:
            info.notes.append("Failed to extract firmware archive")
            return info
    else:
        # Try to recover asset name from what we find
        info.asset_name = "iscope_64 (cached)"

    all_files = sorted(str(f.relative_to(extract_dir)) for f in extract_dir.rglob("*") if f.is_file())
    info.all_files = all_files

    # MCU firmware binary
    for f in extract_dir.rglob("Seestar_*.bin"):
        info.mcu_firmware = f.name
        m = re.search(r'Seestar_([\d.]+)\.bin', f.name)
        if m:
            info.mcu_version = m.group(1)
        break

    # Scripts
    info.scripts = [f for f in all_files if f.endswith('.sh') or f.endswith('.py')]

    # Binaries (no extension, executable-ish names, in bin/)
    info.binaries = [
        f for f in all_files
        if '/bin/' in f and '.' not in Path(f).name
        and not Path(f).name.startswith('.')
    ]

    # Key script excerpts
    for f in extract_dir.rglob("network.sh"):
        info.network_sh_excerpt = _slurp(f)
        break
    for f in extract_dir.rglob("bluetooth.sh"):
        info.bluetooth_sh_excerpt = _slurp(f)
        break
    for f in extract_dir.rglob("update_package.sh"):
        info.update_sh_excerpt = _slurp(f)
        break

    # ASIAIR software version from config file (version_string=X.XX)
    # Newer format: config is in deb-build/asiair_armhf/home/pi/ASIAIR/config
    for f in extract_dir.rglob("config"):
        if f.is_file():
            text = f.read_text(errors='ignore')
            m = re.search(r'^version_string\s*=\s*(.+)$', text, re.MULTILINE)
            if m:
                info.asiair_deb_version = m.group(1).strip()
                break

    # Older format: version is inside deb/asiair_armhf.deb — extract and read config
    if not info.asiair_deb_version:
        for deb_f in extract_dir.rglob("asiair*.deb"):
            try:
                import subprocess
                deb_extract_dir = deb_f.parent / "_deb_extract"
                subprocess.run(
                    ["dpkg-deb", "-x", str(deb_f), str(deb_extract_dir)],
                    capture_output=True, check=True
                )
                for cfg in deb_extract_dir.rglob("config"):
                    if cfg.is_file():
                        text = cfg.read_text(errors='ignore')
                        mv = re.search(r'^version_string\s*=\s*(.+)$', text, re.MULTILINE)
                        if mv:
                            info.asiair_deb_version = mv.group(1).strip()
                            break
                shutil.rmtree(deb_extract_dir, ignore_errors=True)
            except Exception:
                pass
            if info.asiair_deb_version:
                break

    return info


def render_firmware_report(info: FirmwareInfo) -> str:
    lines = [
        f"# Firmware Analysis — App v{info.apk_version}",
        "",
        "## Overview",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| App version | {info.apk_version} |",
        f"| Asset name | {info.asset_name} |",
        f"| MCU firmware | {info.mcu_firmware or 'not found'} |",
        f"| MCU version | {info.mcu_version or 'unknown'} |",
        f"| ASIAIR deb version | {info.asiair_deb_version or 'unknown'} |",
        "",
    ]

    if info.notes:
        lines += ["## Notes", ""]
        for n in info.notes:
            lines.append(f"- {n}")
        lines.append("")

    if info.binaries:
        lines += ["## Binaries", ""]
        for b in sorted(info.binaries):
            lines.append(f"- `{b}`")
        lines.append("")

    if info.scripts:
        lines += ["## Scripts", ""]
        for s in sorted(info.scripts):
            lines.append(f"- `{s}`")
        lines.append("")

    if info.network_sh_excerpt:
        lines += ["## network.sh (first 60 lines)", "", "```bash", info.network_sh_excerpt, "```", ""]

    if info.bluetooth_sh_excerpt:
        lines += ["## bluetooth.sh (first 60 lines)", "", "```bash", info.bluetooth_sh_excerpt, "```", ""]

    if info.update_sh_excerpt:
        lines += ["## update_package.sh (first 60 lines)", "", "```bash", info.update_sh_excerpt, "```", ""]

    lines += ["## All Files", ""]
    for f in info.all_files:
        lines.append(f"- `{f}`")

    return "\n".join(lines)


def render_firmware_comparison(a: FirmwareInfo, b: FirmwareInfo) -> str:
    lines = [
        f"# Firmware Comparison: v{a.apk_version} → v{b.apk_version}",
        "",
        "## Version Changes",
        f"| | v{a.apk_version} | v{b.apk_version} |",
        f"|--|--|--|",
        f"| MCU firmware | {a.mcu_firmware or '?'} | {b.mcu_firmware or '?'} |",
        f"| MCU version | {a.mcu_version or '?'} | {b.mcu_version or '?'} |",
        f"| ASIAIR deb | {a.asiair_deb_version or '?'} | {b.asiair_deb_version or '?'} |",
        "",
    ]

    a_files = set(a.all_files)
    b_files = set(b.all_files)
    added = sorted(b_files - a_files)
    removed = sorted(a_files - b_files)

    if added:
        lines += [f"## Files Added ({len(added)})", ""]
        for f in added:
            lines.append(f"- `{f}`")
        lines.append("")

    if removed:
        lines += [f"## Files Removed ({len(removed)})", ""]
        for f in removed:
            lines.append(f"- `{f}`")
        lines.append("")

    if not added and not removed:
        lines += ["## File Changes", "", "No file additions or removals.", ""]

    return "\n".join(lines)


def save_firmware_data(info: FirmwareInfo, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    d = asdict(info)
    (out_dir / "firmware.json").write_text(json.dumps(d, indent=2))


def load_firmware_data(version: str, output_dir: Path) -> FirmwareInfo | None:
    path = output_dir / f"v{version}" / "firmware.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    return FirmwareInfo(**d)
