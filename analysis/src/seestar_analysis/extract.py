"""
Extract structured data from a decompiled Seestar APK source tree.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class VersionInfo:
    version: str = ""
    firmware_version: str = ""
    firmware_version_64: str = ""
    fw_need_update_version: str = ""
    fw_force_upgrade_below: str = ""
    api_base_url: str = ""
    api_astro_url: str = ""
    pub_key: str = ""


@dataclass
class Command:
    name: str
    method: str
    params: list[str] = field(default_factory=list)
    returns: list[str] = field(default_factory=list)


@dataclass
class ApiEndpoint:
    method: str
    path: str
    description: str = ""


@dataclass
class BleInfo:
    service_uuid: str = ""
    write_char_uuid: str = ""
    read_char_uuid: str = ""
    notify_char_uuid: str = ""
    mtu: int = 0
    protocol_methods: list[str] = field(default_factory=list)


@dataclass
class VersionData:
    version: str
    info: VersionInfo = field(default_factory=VersionInfo)
    commands: list[Command] = field(default_factory=list)
    endpoints: list[ApiEndpoint] = field(default_factory=list)
    ble: BleInfo = field(default_factory=BleInfo)
    permissions: list[str] = field(default_factory=list)
    update_mechanism: str = ""
    raw_notes: list[str] = field(default_factory=list)


def _read(path: Path) -> str:
    try:
        return path.read_text(errors='ignore')
    except Exception:
        return ""


def _find_files(sources: Path, pattern: str) -> list[Path]:
    return list(sources.rglob(pattern))


def extract_version_info(sources: Path, data: VersionData):
    # ZConfig.java
    for f in _find_files(sources, "ZConfig.java"):
        text = _read(f)
        for attr, pattern in [
            ("firmware_version", r'firmwareVersionName\s*=\s*"([^"]+)"'),
            ("firmware_version_64", r'firmwareVersionName64\s*=\s*"([^"]+)"'),
        ]:
            m = re.search(pattern, text)
            if m:
                setattr(data.info, attr, m.group(1))

    # DeviceStateData.java — getFwNeedUpdateVersion / getNeedForceFwUpgrade
    for f in _find_files(sources, "DeviceStateData.java"):
        text = _read(f)
        m = re.search(r'getFwNeedUpdateVersionName[^{]*\{[^}]*return\s*"([^"]+)"', text)
        if m:
            data.info.fw_need_update_version = m.group(1)
        m = re.search(r'getFwVersion\(\)\s*[<>]=?\s*(\d+)', text)
        if m:
            ver_int = int(m.group(1))
            major = ver_int // 100
            minor = ver_int % 100
            data.info.fw_force_upgrade_below = f"{major}.{minor}"

    # ConstantsBase.java / Constants.java
    for name in ["ConstantsBase.java", "Constants.java"]:
        for f in _find_files(sources, name):
            text = _read(f)
            for attr, pattern in [
                ("pub_key", r'PUB_KEY\s*=\s*"([^"]+)"'),
                ("api_base_url", r'API_BASE\s*=\s*"([^"]+)"'),
                ("api_astro_url", r'API_ASTRO\s*=\s*"([^"]+)"'),
            ]:
                m = re.search(pattern, text)
                if m and not getattr(data.info, attr):
                    setattr(data.info, attr, m.group(1))

    # Fallback: grep for api.seestar.com
    if not data.info.api_base_url:
        for f in _find_files(sources, "*.java"):
            text = _read(f)
            m = re.search(r'"(https://api\.seestar\.com[^"]*)"', text)
            if m:
                data.info.api_base_url = m.group(1).rstrip('/')
                break


def extract_commands(sources: Path, data: VersionData):
    """Extract all socket commands from *Cmd.java files."""
    seen = set()
    for f in _find_files(sources, "*Cmd.java"):
        text = _read(f)
        # Find method name from encodeCommand
        # Pattern 1: put("method", "pi_xxx")
        m = re.search(r'put\s*\(\s*"method"\s*,\s*"([^"]+)"', text)
        if not m:
            # Pattern 2: put(FirebaseAnalytics.Param.METHOD, "pi_xxx") or put(SOME_CONST, "pi_xxx")
            m = re.search(r'put\s*\(\s*\w[\w.]+METHOD\w*\s*,\s*"([^"]+)"', text)
        if not m:
            # Pattern 3: jSONObject.put(X, "pi_xxx") — grab any quoted string after a comma following put(
            m = re.search(r'\.put\s*\([^,]+,\s*"(pi_[^"]+)"', text)
        if m:
            method = m.group(1)
            if method not in seen:
                seen.add(method)
                # Extract params from decodeData
                params = re.findall(r'opt(?:String|Int|Double|Boolean|Long)\("([^"]+)"', text)
                params = [p for p in params if p not in ('id', 'method', 'jsonrpc', 'code', 'error')]
                data.commands.append(Command(
                    name=f.stem,
                    method=method,
                    params=list(dict.fromkeys(params)),
                ))

    data.commands.sort(key=lambda c: c.method)


def _load_constants(sources: Path) -> dict[str, str]:
    """Load all string constants from ApiConst/Constants files for annotation resolution."""
    constants = {}
    for name in ["ApiConst.java", "ApiConstants.java", "Constants.java", "Urls.java"]:
        for f in _find_files(sources, name):
            text = _read(f)
            for m in re.finditer(r'String\s+(\w+)\s*=\s*"([^"]+)"', text):
                constants[m.group(1)] = m.group(2)
    return constants


def extract_endpoints(sources: Path, data: VersionData):
    """Extract API endpoints from Retrofit interface definitions."""
    constants = _load_constants(sources)
    seen = set()

    # Match @GET/@POST etc with either a literal string or a constant reference
    http_pattern = re.compile(
        r'@(GET|POST|PUT|PATCH|DELETE|HEAD)\(([^)]+)\)\s*\n\s*[\w<>, ]+\s+(\w+)\('
    )

    for f in _find_files(sources, "*.java"):
        text = _read(f)
        if not any(f'@{m}(' in text for m in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')):
            continue
        for m in http_pattern.finditer(text):
            http_method, raw_path, func_name = m.groups()
            raw_path = raw_path.strip()
            # Resolve: either "literal" or ClassName.CONST_NAME
            if raw_path.startswith('"'):
                path = raw_path.strip('"')
            else:
                # Try to resolve constant — e.g. ApiConst.POST_ASTRO_LOGIN → const name
                const_name = raw_path.split('.')[-1]
                path = constants.get(const_name, raw_path)

            if not path.startswith('/') and not path.startswith('http') and '.' in path:
                continue  # Unresolved constant, skip

            key = f"{http_method}:{path}"
            if key not in seen:
                seen.add(key)
                data.endpoints.append(ApiEndpoint(
                    method=http_method,
                    path=path,
                    description=func_name,
                ))
    data.endpoints.sort(key=lambda e: e.path)


def extract_ble(sources: Path, data: VersionData):
    """Extract BLE UUIDs and protocol methods."""
    for f in _find_files(sources, "BleUtils*.java"):
        text = _read(f)
        for attr, pattern in [
            ("service_uuid", r'[Ss]ervice.*?"(850e[0-9a-f-]{30,})"'),
            ("write_char_uuid", r'(?:write|notify|char).*?"(850e[0-9a-f-]{30,})"'),
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m and not getattr(data.ble, attr):
                setattr(data.ble, attr, m.group(1))

        # All 850e UUIDs
        uuids = re.findall(r'"(850e[0-9a-f\-]{30,})"', text)
        if uuids:
            unique = list(dict.fromkeys(uuids))
            if len(unique) >= 1 and not data.ble.service_uuid:
                data.ble.service_uuid = unique[0]
            if len(unique) >= 2 and not data.ble.write_char_uuid:
                data.ble.write_char_uuid = unique[1]
            if len(unique) >= 3 and not data.ble.read_char_uuid:
                data.ble.read_char_uuid = unique[2]

        # BLE protocol methods
        methods = re.findall(r'"ble_method"\s*,\s*"([^"]+)"', text)
        methods += re.findall(r'ble_method.*?"([a-z_]+)"', text)
        data.ble.protocol_methods.extend(m for m in methods if m not in data.ble.protocol_methods)

        # MTU
        m = re.search(r'requestMtu\((\d+)\)', text)
        if m:
            data.ble.mtu = int(m.group(1))


def extract_update_mechanism(sources: Path, data: VersionData):
    """Detect whether update uses apt or rsync."""
    for f in _find_files(sources, "update_package.sh"):
        text = _read(f)
        if 'apt' in text and 'install' in text:
            data.update_mechanism = "apt"
        elif 'rsync' in text:
            data.update_mechanism = "rsync"
        else:
            data.update_mechanism = "unknown"
        return

    # Check embedded in firmware blob references
    for f in list(_find_files(sources, "*.java"))[:50]:
        text = _read(f)
        if 'apt install' in text:
            data.update_mechanism = "apt"
            return
        if 'rsync' in text and 'update' in text:
            data.update_mechanism = "rsync"
            return

    data.update_mechanism = "unknown"


def extract_all(version: str, sources: Path) -> VersionData:
    """Run all extractors and return a VersionData."""
    data = VersionData(version=version)
    data.info.version = version

    extract_version_info(sources, data)
    extract_commands(sources, data)
    extract_endpoints(sources, data)
    extract_ble(sources, data)
    extract_update_mechanism(sources, data)

    return data


def save(data: VersionData, out_dir: Path):
    """Save extracted data as JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "data.json"
    path.write_text(json.dumps(asdict(data), indent=2))
    return path


def load(version: str, output_dir: Path) -> VersionData | None:
    """Load previously extracted data."""
    path = output_dir / f"v{version}" / "data.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    d = VersionData(version=raw["version"])
    d.info = VersionInfo(**raw["info"])
    d.commands = [Command(**c) for c in raw["commands"]]
    d.endpoints = [ApiEndpoint(**e) for e in raw["endpoints"]]
    d.ble = BleInfo(**raw["ble"])
    d.permissions = raw.get("permissions", [])
    d.update_mechanism = raw.get("update_mechanism", "")
    d.raw_notes = raw.get("raw_notes", [])
    return d
