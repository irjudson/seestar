#!/usr/bin/env python3
"""
Seestar Firmware Flash Tool
Direct socket-based firmware update utility

WARNING: This tool directly communicates with Seestar firmware update protocol.
- Use at your own risk
- May brick your device
- Not officially supported
- Intended for research/recovery purposes only

Usage:
    python seestar_firmware_flash.py <firmware_file> --host <device_ip>
"""

import socket
import json
import hashlib
import argparse
import sys
import time
import os
import base64
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


# Path to Seestar authentication key (same as used in astro-planner)
DEFAULT_KEY_PATH = Path(__file__).parent.parent.parent / "backend" / "secrets" / "seestar_private_key.pem"


def load_private_key(key_path: Path = DEFAULT_KEY_PATH) -> bytes:
    """
    Load RSA private key for Seestar authentication

    Args:
        key_path: Path to PEM-encoded private key

    Returns:
        Private key PEM bytes

    Raises:
        FileNotFoundError: If key file not found
    """
    if not key_path.exists():
        raise FileNotFoundError(
            f"Seestar authentication key not found at {key_path}. "
            "Please ensure the key file exists."
        )

    with open(key_path, "rb") as f:
        return f.read()


def sign_challenge(challenge_str: str, private_key_pem: bytes) -> str:
    """
    Sign authentication challenge using RSA private key

    This implements the authentication mechanism required by firmware 6.45+.
    The challenge is signed (not encrypted) using RSA-SHA1.

    Args:
        challenge_str: Challenge string from get_verify_str
        private_key_pem: PEM-encoded private key bytes

    Returns:
        Base64-encoded signature
    """
    # Load the private key
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=None, backend=default_backend()
    )

    # Sign the challenge using RSA-SHA1 (required by Seestar firmware protocol)
    # SHA1 used for RSA signing (not password hashing), required by hardware
    signature = private_key.sign(
        challenge_str.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA1()  # nosec B303
    )

    # Return base64-encoded signature
    return base64.b64encode(signature).decode("utf-8")


# Minimum firmware_ver_int that implements the set_wifi_country JSON-RPC
# handler on the device. Introduced in fw_2.6.4 (app 5.82).
SET_WIFI_COUNTRY_MIN_FW = 2582


def post_upgrade_set_wifi_country(host: str, country: str = "US", port: int = 4700,
                                   max_wait: int = 360,
                                   pre_upgrade_fw: Optional[int] = None) -> bool:
    """
    After a firmware upgrade, poll port 4700 and wait for the device to reboot.
    Detect reboot by firmware_ver_int CHANGE (not threshold), so this works for
    any upgrade path. Once rebooted, if the NEW firmware supports set_wifi_country
    (>= fw_2.6.4 / 2582), send the JSON-RPC that mirrors the vendor APK's BLE
    ble_connect wifi_country field. Server-side handler invokes network.sh
    country <CC> → reload_country(<CC>): stop hostapd → ccode=<CC> in sh_conf.txt
    → wl country <CC> → autochannel_enabled=1 in AP_*.conf → start hostapd.

    If the new firmware is < 2582 (e.g. upgrading 2.42 → 5.50), the handler
    doesn't exist, so we skip the RPC and just report the reboot is complete.

    Polling starts IMMEDIATELY (no blind timer). Returns True on success
    (reboot seen + either RPC accepted OR skipped for old firmware).
    """
    import time

    print(f"\n{'='*70}")
    print(f"POST-UPGRADE: waiting for reboot + set_wifi_country if new fw supports it")
    print(f"{'='*70}")
    if pre_upgrade_fw is not None:
        print(f"Pre-upgrade firmware_ver_int: {pre_upgrade_fw}")
    print(f"Polling {host}:{port} for firmware_ver_int change (up to {max_wait}s)...")

    deadline = time.time() + max_wait
    poll_interval = 2
    heartbeat_every = 15  # seconds
    polls = 0
    last_seen_fw = pre_upgrade_fw
    last_err = None
    new_fw_int = None
    started = time.time()
    last_heartbeat = started
    # Log that we observed the old firmware at start so the user sees something.
    if pre_upgrade_fw is not None:
        print(f"  [  0s] firmware still {pre_upgrade_fw} (pre-upgrade) — waiting for reboot")
    while time.time() < deadline:
        polls += 1
        sock = None
        status = "unreachable"
        fw_int = None
        fw_str = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            version_event = read_initial_version(sock, timeout=2.0)
            sock.close()
            if version_event is not None:
                fw_int = version_event.get("firmware_ver_int", 0)
                fw_str = version_event.get("firmware_ver_string", "?")
                status = f"firmware={fw_str} ({fw_int})"
                if fw_int != last_seen_fw:
                    elapsed = int(time.time() - started)
                    print(f"  [{elapsed:3d}s] {status} — CHANGED from {last_seen_fw}")
                    last_seen_fw = fw_int
                if pre_upgrade_fw is None or fw_int != pre_upgrade_fw:
                    elapsed = int(time.time() - started)
                    print(f"[+] Reboot into new firmware confirmed after {elapsed}s ({polls} polls)")
                    new_fw_int = fw_int
                    break
            else:
                status = "TCP ok but no Version event"
        except Exception as e:
            last_err = e
            if sock:
                try: sock.close()
                except: pass

        # Heartbeat so user sees polling is alive even when fw hasn't changed.
        if time.time() - last_heartbeat >= heartbeat_every:
            elapsed = int(time.time() - started)
            print(f"  [{elapsed:3d}s] polls={polls} status={status}")
            last_heartbeat = time.time()

        time.sleep(poll_interval)

    if new_fw_int is None:
        print(f"[!] Did not observe firmware_ver_int change within {max_wait}s")
        print(f"    Last seen firmware_ver_int: {last_seen_fw}, last error: {last_err}")
        print(f"[!] If sound-33 'WiFi abnormal' fired, do NOT 3s-reset.")
        return False

    # Decide whether to send set_wifi_country based on the NEW firmware version.
    if new_fw_int < SET_WIFI_COUNTRY_MIN_FW:
        print(f"[+] New firmware ({new_fw_int}) < {SET_WIFI_COUNTRY_MIN_FW} — set_wifi_country")
        print(f"    handler not present. Skipping RPC; upgrade complete.")
        return True
    else:
        print(f"[!] Device did not come back in {max_wait}s (last error: {last_err})")
        print(f"[!] If sound-33 'WiFi abnormal' fired, do NOT 3s-reset.")
        print(f"[!] Try manually once reachable:  python3 tools/set_wifi_country.py --host {host}")
        return False

    # Brief grace period to let zwoair_imager finish init (port 4700 listener
    # may accept the TCP connection before the JSON-RPC handler is ready).
    print(f"[*] 3s grace for zwoair_imager to finish startup...")
    time.sleep(3)

    # Send set_wifi_country JSON-RPC.
    print(f"[*] sending set_wifi_country(country={country})...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        # Drain the initial Version event so it doesn't clobber our response.
        sock.settimeout(2)
        try:
            initial = sock.recv(4096)
            for line in initial.decode("utf-8", errors="replace").split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if parsed.get("Event") == "Version":
                        print(f"[+] device Version: firmware={parsed.get('firmware_ver_string')} "
                              f"({parsed.get('firmware_ver_int')}), is_verified={parsed.get('is_verified')}")
                except json.JSONDecodeError:
                    pass
        except socket.timeout:
            pass

        cmd = {"id": 1000, "method": "set_wifi_country",
               "params": {"country": country}, "jsonrpc": "2.0"}
        payload = json.dumps(cmd) + "\r\n"
        sock.sendall(payload.encode("utf-8"))

        sock.settimeout(15)
        buf = b""
        start = time.time()
        result = None
        while time.time() - start < 15:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                for raw in buf.decode("utf-8", errors="replace").split("\n"):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if parsed.get("id") == 1000:
                        result = parsed
                        break
                if result is not None:
                    break
            except socket.timeout:
                break
        sock.close()

        if result is None:
            print(f"[!] No response to set_wifi_country within 15s")
            return False

        code = result.get("code", result.get("result"))
        print(f"[+] response: {json.dumps(result)}")
        if code == 0:
            print(f"[+] set_wifi_country accepted. Server-side reload_country(\"{country}\") running:")
            print(f"    stop hostapd → ccode={country} → wl country {country} → autochannel_enabled=1 → start hostapd")
            print(f"    AP should re-stabilize within ~5s. Subsequent boots will be clean.")
            return True
        else:
            print(f"[!] set_wifi_country returned code/result={code}")
            return False
    except Exception as e:
        print(f"[!] Error calling set_wifi_country: {e}")
        return False


def read_initial_version(sock: socket.socket, timeout: float = 3.0) -> Optional[dict]:
    """
    On connect, the device immediately emits a Version event JSON line with
    firmware_ver_int, firmware_ver_string, and is_verified. The `is_verified`
    boolean is the vendor's gate: if true the device does NOT need RSA-SHA1
    challenge/response auth (older firmware ≤ app 5.97 / fw_2.7.0), if false
    the client must run get_verify_str + verify_client (fw_3.0.0 / app 6.45+).
    This mirrors what v3.0.0+ APKs do via pi_is_verified / is_verified.

    Reads up to `timeout` seconds waiting for the first newline-terminated JSON
    object. Returns parsed event dict, or None if nothing arrived.
    """
    import time
    sock.settimeout(timeout)
    buf = b""
    start = time.time()
    while time.time() - start < timeout:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break
        except socket.timeout:
            break
        except Exception:
            return None

    for raw in buf.decode("utf-8", errors="replace").split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if parsed.get("Event") == "Version":
            return parsed
    return None


def authenticate_socket(sock: socket.socket, private_key_pem: bytes, command_id: int = 1) -> bool:
    """
    Perform 2-step authentication for firmware 6.45+

    Step 1: Request challenge string via get_verify_str
    Step 2: Sign challenge and send via verify_client

    Args:
        sock: Connected socket to device
        private_key_pem: PEM-encoded private key bytes
        command_id: Starting command ID

    Returns:
        True if authentication successful, False otherwise
    """
    try:
        # Step 1: Get challenge string
        print(f"[*] Step 1: Requesting authentication challenge...")
        challenge_cmd = {
            "id": command_id,
            "method": "get_verify_str",
            "jsonrpc": "2.0"
        }

        cmd_str = json.dumps(challenge_cmd) + "\r\n"
        sock.sendall(cmd_str.encode('utf-8'))

        # Receive challenge response
        sock.settimeout(5)
        response_data = sock.recv(4096).decode('utf-8').strip()

        # Parse response (may be multiple lines)
        challenge_str = None
        for line in response_data.split('\n'):
            line = line.strip()
            if line:
                try:
                    parsed = json.loads(line)
                    if 'result' in parsed and 'str' in parsed['result']:
                        challenge_str = parsed['result']['str']
                        print(f"[+] Received challenge (length: {len(challenge_str)})")
                        break
                except json.JSONDecodeError:
                    continue

        if not challenge_str:
            print(f"[!] No challenge string in response: {response_data}")
            return False

        # Step 2: Sign challenge and send verification
        print(f"[*] Step 2: Signing challenge and authenticating...")
        signed_challenge = sign_challenge(challenge_str, private_key_pem)

        verify_cmd = {
            "id": command_id + 1,
            "method": "verify_client",
            "params": {
                "sign": signed_challenge,
                "data": challenge_str
            },
            "jsonrpc": "2.0"
        }

        cmd_str = json.dumps(verify_cmd) + "\r\n"
        sock.sendall(cmd_str.encode('utf-8'))

        # Receive verification response
        response_data = sock.recv(4096).decode('utf-8').strip()

        # Parse response
        for line in response_data.split('\n'):
            line = line.strip()
            if line:
                try:
                    parsed = json.loads(line)
                    result_code = parsed.get('result', parsed.get('code', -1))
                    if result_code == 0:
                        print(f"[+] Authentication successful")
                        return True
                    else:
                        error = parsed.get('error', 'unknown error')
                        print(f"[!] Authentication failed: {error} (code {result_code})")
                        return False
                except json.JSONDecodeError:
                    continue

        print(f"[!] No verification response: {response_data}")
        return False

    except Exception as e:
        print(f"[!] Authentication error: {e}")
        return False


def check_device_ready_for_update(host: str, port: int = 4700, key_path: Path = DEFAULT_KEY_PATH) -> Tuple[Optional[int], bool, str]:
    """
    Query device to check if ready for firmware update
    Uses port 4700 (SOCKET - normal device commands) not 4350 (FW_SOCKET - firmware only)
    Authenticates using RSA challenge-response before querying device
    Returns: (platform, is_ready, reason)
        platform: 1 for x64, None or other for x86
        is_ready: True if safe to update
        reason: Description of status
    """
    print(f"[*] Checking device status at {host}:{port} (normal command socket)...")

    try:
        # Load private key for authentication
        print(f"[*] Loading authentication key from {key_path}...")
        try:
            private_key_pem = load_private_key(key_path)
            print(f"[+] Private key loaded successfully")
        except FileNotFoundError as e:
            print(f"[!] {e}")
            return None, False, "Authentication key not found"

        # Connect to device
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print(f"[+] Connected to {host}:{port}")

        # Read the initial Version event the device emits on connect.
        # Two signals gate RSA-SHA1 challenge/response auth:
        #   1. firmware_ver_int < 2645 (app < 6.45 / fw < 3.0.0) — device doesn't
        #      implement get_verify_str at all; calling it returns "method not found".
        #   2. is_verified=true — device says it doesn't need verification.
        # The vendor APK v3.0.0+ uses both signals. Older APKs (v2.6.1, 2.6.4, 2.7.0)
        # have NO auth code and push firmware without it.
        AUTH_MIN_FW_INT = 2645
        version_event = read_initial_version(sock)
        needs_auth = True
        if version_event is not None:
            fw_str = version_event.get("firmware_ver_string", "?")
            fw_int = version_event.get("firmware_ver_int", 0)
            is_verified = version_event.get("is_verified", False)
            print(f"[+] Device Version event: firmware={fw_str} ({fw_int}), is_verified={is_verified}")
            if fw_int and fw_int < AUTH_MIN_FW_INT:
                print(f"[+] firmware_ver_int {fw_int} < {AUTH_MIN_FW_INT} — this firmware doesn't implement auth; skipping")
                needs_auth = False
            elif is_verified:
                print(f"[+] Device reports is_verified=true — skipping RSA auth")
                needs_auth = False
        else:
            print(f"[*] No Version event received on connect — assuming auth required")

        # Authenticate with device (firmware 6.45+ with is_verified=false requires this)
        if needs_auth:
            if not authenticate_socket(sock, private_key_pem, command_id=1):
                sock.close()
                return None, False, "Authentication failed"

        # Now send get_device_state (use command ID 3 since we used 1 and 2 for auth)
        command = {
            "id": 3,
            "method": "get_device_state",
            "jsonrpc": "2.0"
        }

        # Send command
        command_str = json.dumps(command) + "\r\n"
        sock.sendall(command_str.encode('utf-8'))

        # Receive responses (may get multiple: Version event + get_device_state response)
        sock.settimeout(5)
        response_data = b""

        # Keep reading for a few seconds to get all responses
        import time
        start_time = time.time()
        while time.time() - start_time < 3:  # Read for 3 seconds
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
            except:
                break

        # Parse response (device may send multiple JSON objects)
        response_str = response_data.decode('utf-8').strip()

        print(f"\n[*] Raw response from device:")
        print(f"{'='*70}")
        print(response_str)
        print(f"{'='*70}\n")

        # Split by newlines and parse all JSON objects
        lines = response_str.split('\n')
        response = None
        for line in lines:
            line = line.strip()
            if line:
                try:
                    parsed = json.loads(line)

                    # Skip any Event messages (Version, ScopeTrack, etc.)
                    if 'Event' in parsed:
                        print(f"[*] Skipping {parsed['Event']} event")
                        continue

                    # Look for our specific response (id=3, method=get_device_state)
                    if parsed.get('id') == 3 and 'result' in parsed:
                        response = parsed
                        print(f"[+] Found get_device_state response")
                        break

                    # Check for error response to OUR command (has our id=3)
                    if parsed.get('id') == 3 and 'error' in parsed:
                        error_msg = parsed.get('error', 'Unknown')
                        error_code = parsed.get('code', 'Unknown')
                        print(f"[!] Device error: {error_msg} (code {error_code})")
                        if error_code == 103:
                            print(f"[!] Method 'get_device_state' not supported by this firmware version")
                            print(f"[*] Platform detection unavailable - defaulting to X86")
                            print(f"[*] Cannot verify battery status - proceed with caution")
                        return None, False, f"Device error: {error_msg}"

                except json.JSONDecodeError as e:
                    print(f"[!] Failed to parse line as JSON: {e}")
                    continue

        sock.close()

        if not response:
            print(f"[!] No get_device_state response found")
            print(f"[!] Device firmware may not support this command")
            print(f"[*] Defaulting to X86 firmware")
            print(f"[*] Cannot verify battery status - proceed with caution")
            return None, False, "No device response"

        # Extract firmware_platform
        if 'result' in response and 'device' in response['result']:
            device = response['result']['device']
            firmware_platform = device.get('firmware_platform')

            # Show device summary
            print(f"\n[+] Device Information:")
            print(f"    Name     : {device.get('name', 'Unknown')}")
            print(f"    Model    : {device.get('model', 'Unknown')}")
            print(f"    Firmware : {device.get('firmware_ver_string', 'Unknown')}")
            print(f"    Platform : {firmware_platform if firmware_platform is not None else 'Not Set'}")

            # Show full device JSON
            print(f"\n[*] Full Device JSON:")
            print(f"{'='*70}")
            print(json.dumps(device, indent=2))
            print(f"{'='*70}")

            # Show platform decision
            # Check pi_status for battery and update status
            pi_status = response.get('result', {}).get('pi_status', {})
            battery_capacity = pi_status.get('battery_capacity', 0)
            battery_in_charging = pi_status.get('battery_in_charging', 0)

            print(f"\n[+] Battery Status:")
            print(f"    Capacity  : {battery_capacity}%")
            print(f"    Charging  : {'Yes' if battery_in_charging == 1 else 'No'}")

            # Safety checks (from DeviceFwFragment.java:298)
            is_ready = True
            reason = "Device ready for update"

            if battery_capacity < 20 and battery_in_charging != 1:
                is_ready = False
                reason = f"Battery too low ({battery_capacity}%) and not charging. Needs ≥20% or charging."
                print(f"\n[!] WARNING: {reason}")
            else:
                print(f"\n[+] Battery check: PASSED")

            # Show platform decision
            print(f"\n[+] Platform Detection:")
            print(f"    firmware_platform: {firmware_platform if firmware_platform is not None else 'Not Set'}")
            if firmware_platform == 1:
                print(f"    Decision: Using X64 firmware")
            else:
                if firmware_platform is None:
                    print(f"    Decision: Using X86 firmware (default)")
                else:
                    print(f"    Decision: Using X86 firmware")

            return firmware_platform, is_ready, reason

    except Exception as e:
        print(f"[!] Failed to check device status: {e}")

    return None, False, "Failed to query device"


class SeestarFirmwareFlasher:
    """Direct firmware flasher using Seestar socket protocol"""

    # Port constants from DeviceFwFragment.java
    CMD_PORT = 4350      # Command socket
    FILE_PORT = 4361     # File transfer socket

    # Timeout settings
    CONNECT_TIMEOUT = 10
    RECV_TIMEOUT = 30

    def __init__(self, host: str, firmware_file: str, is_x64: bool = False):
        self.host = host
        self.firmware_file = Path(firmware_file)
        self.is_x64 = is_x64

        # Sockets
        self.cmd_socket: Optional[socket.socket] = None
        self.file_socket: Optional[socket.socket] = None

        # Firmware metadata
        self.firmware_size = 0
        self.firmware_md5 = ""

        # State
        self.connected = False

        # Mock update timer (from DeviceFwFragment.java:87-88)
        # Android app uses fake timers since device doesn't send progress
        self.MOCK_UPDATE_DURATION_X86 = 200  # 200 seconds for x86
        self.MOCK_UPDATE_DURATION_X64 = 60   # 60 seconds for x64

    def calculate_md5(self) -> str:
        """Calculate MD5 checksum of firmware file"""
        print(f"[*] Calculating MD5 checksum of {self.firmware_file}...")

        md5_hash = hashlib.md5()
        with open(self.firmware_file, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                md5_hash.update(chunk)

        md5_checksum = md5_hash.hexdigest()
        print(f"[+] MD5: {md5_checksum}")
        return md5_checksum

    def validate_firmware_file(self) -> bool:
        """Validate firmware file exists and get metadata"""
        if not self.firmware_file.exists():
            print(f"[!] Error: Firmware file not found: {self.firmware_file}")
            return False

        self.firmware_size = self.firmware_file.stat().st_size
        print(f"[+] Firmware file: {self.firmware_file}")
        print(f"[+] File size: {self.firmware_size:,} bytes ({self.firmware_size / 1024 / 1024:.2f} MB)")

        if self.firmware_size == 0:
            print(f"[!] Error: Firmware file is empty")
            return False

        self.firmware_md5 = self.calculate_md5()
        return True

    def connect_sockets(self) -> bool:
        """Connect to both command and file transfer sockets"""
        print(f"\n[*] Connecting to Seestar at {self.host}...")

        try:
            # Connect file socket first (like the app does)
            print(f"[*] Connecting to file socket (port {self.FILE_PORT})...")
            self.file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.file_socket.settimeout(self.CONNECT_TIMEOUT)
            self.file_socket.connect((self.host, self.FILE_PORT))
            print(f"[+] File socket connected")

            # Connect command socket
            print(f"[*] Connecting to command socket (port {self.CMD_PORT})...")
            self.cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_socket.settimeout(self.CONNECT_TIMEOUT)
            self.cmd_socket.connect((self.host, self.CMD_PORT))
            print(f"[+] Command socket connected")

            # Device automatically sends Version event after connection
            self.cmd_socket.settimeout(10)
            version_event = self.recv_response(timeout=10)

            if version_event and 'Event' in version_event and version_event['Event'] == 'Version':
                print(f"[+] Device ready: {version_event.get('name', 'Unknown')}")
            else:
                print(f"[!] Warning: Did not receive expected Version event")
                print(f"    Got: {version_event}")

            self.connected = True
            return True

        except socket.timeout:
            print(f"[!] Connection timeout - is the device online?")
            return False
        except ConnectionRefusedError:
            print(f"[!] Connection refused - are the ports correct?")
            return False
        except Exception as e:
            print(f"[!] Connection error: {e}")
            return False

    def send_command(self, command: dict) -> bool:
        """Send JSON command over command socket"""
        try:
            # Format as JSON with newline (like the app does)
            cmd_str = json.dumps(command) + '\n'
            cmd_bytes = cmd_str.encode('utf-8')

            print(f"[*] Sending command: {json.dumps(command, indent=2)}")
            self.cmd_socket.sendall(cmd_bytes)
            return True

        except Exception as e:
            print(f"[!] Error sending command: {e}")
            return False

    def recv_response(self, timeout: int = None) -> Optional[dict]:
        """Receive JSON response from command socket"""
        try:
            if timeout:
                self.cmd_socket.settimeout(timeout)

            # Receive data until newline
            data = b''
            while True:
                chunk = self.cmd_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break

            if not data:
                return None

            # Parse JSON
            response_str = data.decode('utf-8').strip()
            response = json.loads(response_str)

            # Only show response for important messages (errors, begin_recv response)
            if 'code' in response or 'error' in response:
                print(f"[*] Device response: {json.dumps(response, indent=2)}")

            return response

        except socket.timeout:
            return None  # Timeout is normal during monitoring
        except json.JSONDecodeError as e:
            print(f"[!] Invalid JSON response: {e}")
            print(f"    Raw data: {data}")
            return None
        except Exception as e:
            print(f"[!] Error receiving response: {e}")
            return None

    def send_begin_recv(self) -> bool:
        """Send begin_recv command to start firmware update"""

        # Send begin_recv command (DeviceFwFragment.java:568-586)
        # Note: Version event was already received during connect_sockets()
        print(f"\n[*] Sending begin_recv command...")
        command = {
            "id": 100,
            "method": "begin_recv",
            "params": [{
                "file_name": "air",
                "run_update": True,
                "file_len": self.firmware_size,
                "md5": self.firmware_md5
            }]
        }

        if not self.send_command(command):
            return False

        print(f"[*] Waiting for device response...")
        response = self.recv_response(timeout=self.RECV_TIMEOUT)

        if not response:
            print(f"[!] No response from device")
            return False

        # Check for success (code=0) - from DeviceFwFragment.java:428-436
        if 'id' in response and response['id'] == 100:
            if 'code' in response:
                code = response['code']
                if code == 0:
                    print(f"[+] Device accepted firmware transfer!")
                    return True
                elif code == 524:
                    print(f"[!] Device error 524: Firmware update already in progress")
                    print(f"    Please wait for current update to finish or reboot device")
                    return False
                else:
                    error_msg = response.get('error', 'Unknown error')
                    print(f"[!] Device rejected update - Code {code}: {error_msg}")
                    return False

        print(f"[!] Unexpected response format")
        return False

    def transfer_firmware(self, chunk_size: int = 8192) -> bool:
        """Transfer firmware file over file socket"""
        print(f"\n[*] Starting firmware transfer...")
        print(f"[*] Transferring {self.firmware_size:,} bytes...")

        try:
            bytes_sent = 0
            last_progress = 0

            with open(self.firmware_file, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    self.file_socket.sendall(chunk)
                    bytes_sent += len(chunk)

                    # Update progress every 5%
                    progress = int((bytes_sent / self.firmware_size) * 100)
                    if progress >= last_progress + 5:
                        print(f"[*] Progress: {progress}% ({bytes_sent:,} / {self.firmware_size:,} bytes)")
                        last_progress = progress

            print(f"[+] Transfer complete: {bytes_sent:,} bytes sent")

            if bytes_sent != self.firmware_size:
                print(f"[!] Warning: Bytes sent ({bytes_sent}) != file size ({self.firmware_size})")
                return False

            return True

        except Exception as e:
            print(f"[!] Error during transfer: {e}")
            return False

    def wait_for_update_completion(self) -> bool:
        """
        Wait for firmware update to complete using mock timer
        The device doesn't send real progress updates, so we wait a fixed time
        like the Android app does (DeviceFwFragment.java:776-843)
        """
        duration = self.MOCK_UPDATE_DURATION_X64 if self.is_x64 else self.MOCK_UPDATE_DURATION_X86
        platform_name = "X64" if self.is_x64 else "X86"

        print(f"\n{'='*70}")
        print(f"WAITING FOR UPDATE TO COMPLETE")
        print(f"{'='*70}")
        print(f"Platform: {platform_name}")
        print(f"Estimated duration: {duration} seconds (~{duration//60} minutes)")
        print(f"\nNOTE: The device does NOT send progress updates.")
        print(f"      The Android app just waits {duration}s and hopes it's done.")
        print(f"      This is the same approach.\n")

        print(f"LED Status Sequence:")
        print(f"  1. Blinking Yellow → Update in progress")
        print(f"  2. Solid Yellow    → Update finishing up")
        print(f"  3. Green           → Update succeeded!")
        print(f"     OR")
        print(f"     Red             → Update failed\n")

        print(f"[*] Starting {duration} second countdown...")

        start_time = time.time()
        last_progress = -1

        while True:
            elapsed = time.time() - start_time

            if elapsed >= duration:
                break

            # Calculate progress (0-99%, never 100 until complete)
            progress = min(int((elapsed / duration) * 100), 99)

            # Update every 5% or every 10 seconds
            if progress >= last_progress + 5 or (int(elapsed) % 10 == 0 and int(elapsed) != int(elapsed - 1)):
                remaining = duration - elapsed
                mins_remaining = int(remaining // 60)
                secs_remaining = int(remaining % 60)
                print(f"[*] Progress: {progress}% | Elapsed: {int(elapsed)}s | Remaining: {mins_remaining}m {secs_remaining}s")
                last_progress = progress

            time.sleep(1)

        print(f"\n[+] Update timer complete ({duration} seconds elapsed)")
        print(f"\n{'='*70}")
        print(f"UPDATE TIMER COMPLETED")
        print(f"{'='*70}")
        print(f"The firmware should now be installed on the device.")
        print(f"\nCheck the LED on your device:")
        print(f"\nExpected LED Sequence:")
        print(f"  1. Blinking Yellow → Solid Yellow → GREEN = Success!")
        print(f"  2. Blinking Yellow → RED = Failed")
        print(f"\nCurrent LED Status:")
        print(f"  - GREEN LED        : ✓ Success! Update completed")
        print(f"  - RED LED          : ✗ Failed - update did not complete")
        print(f"  - BLINKING YELLOW  : Still updating - wait longer")
        print(f"  - SOLID YELLOW     : Almost done - should turn green soon")
        print(f"\nDevice will restart automatically when update completes.")
        print(f"{'='*70}\n")

        return True

    def disconnect(self):
        """Close all socket connections"""
        print(f"\n[*] Disconnecting...")

        if self.cmd_socket:
            try:
                self.cmd_socket.close()
            except:
                pass

        if self.file_socket:
            try:
                self.file_socket.close()
            except:
                pass

        self.connected = False
        print(f"[+] Disconnected")

    def flash_firmware(self) -> bool:
        """Main firmware flashing workflow"""
        try:
            # Show firmware summary
            platform_name = "X64" if self.is_x64 else "X86"
            print(f"\n{'='*70}")
            print(f"FIRMWARE FLASH SUMMARY")
            print(f"{'='*70}")
            print(f"Firmware File : {self.firmware_file}")
            print(f"Platform Type : {platform_name}")
            print(f"Target Device : {self.host}")
            print(f"{'='*70}\n")

            # Step 1: Validate firmware file
            if not self.validate_firmware_file():
                return False

            # Step 2: Connect to device
            if not self.connect_sockets():
                return False

            # Step 3: Send begin_recv command
            if not self.send_begin_recv():
                return False

            # Step 4: Transfer firmware
            if not self.transfer_firmware():
                return False

            # Step 5: Transfer done. Skip the old 200s mock timer — the caller's
            # post_upgrade_set_wifi_country polls port 4700 continuously and
            # detects reboot via firmware_ver_int change, so we don't need a
            # blind wait here. Disconnect cleanly so the post-step starts fresh.
            print(f"\n[+] Transfer accepted by device. Device will run update_package.sh")
            print(f"    and reboot on its own. Caller's post-upgrade step will poll for it.")
            return True

        except KeyboardInterrupt:
            print(f"\n[!] Interrupted by user")
            return False
        except Exception as e:
            print(f"[!] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description='Seestar Firmware Flash Tool - Direct socket-based firmware update',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WARNING: This tool directly communicates with Seestar firmware update protocol.
- Use at your own risk
- May brick your device
- Not officially supported
- Intended for research/recovery purposes only

Example:
    python seestar_firmware_flash.py firmware.bin --host 192.168.1.100
    python seestar_firmware_flash.py --auto --host 192.168.1.100
        """
    )

    parser.add_argument('firmware', nargs='?', help='Path to firmware file')
    parser.add_argument('--host', required=True, help='Seestar device IP address')
    parser.add_argument('--auto', action='store_true',
                       help='Auto-detect platform and use iscope or iscope_64')
    parser.add_argument('--force', action='store_true',
                       help='Force update even if battery is low (NOT RECOMMENDED)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Connect and send begin_recv but do not transfer')
    parser.add_argument('--key', type=Path, default=DEFAULT_KEY_PATH,
                       help=f'Path to Seestar authentication key (default: {DEFAULT_KEY_PATH})')
    parser.add_argument('--set-country', default='US', metavar='CC',
                       help='After upgrade, send set_wifi_country JSON-RPC (default: US). '
                            'Matches what the vendor APK sends via BLE ble_connect. '
                            'Set to "none" to skip.')
    parser.add_argument('--post-upgrade-wait', type=int, default=600,
                       help='Max seconds to wait for device to reboot into the new '
                            'firmware before sending set_wifi_country (default: 600). '
                            'Polls port 4700 continuously starting immediately after '
                            'transfer; detects reboot via firmware_ver_int change.')

    args = parser.parse_args()

    # Known-wedge firmware detection — see UPGRADE_PROBLEM_SUMMARY.md.
    # These versions wedge the BCM43456 WiFi chip with persistent HT Avail
    # timeout on our S50. Only recovery is a full rkdeveloptool reflash.
    # Keyed by substring match on the firmware file path (iscope_2.6.4_*,
    # fw_2.6.4, etc.). Matches deb Version fields from 2.6.4 through 3.1.2.
    WEDGE_KNOWN_BAD = [
        "fw_2.6.4", "iscope_2.6.4", "2582",  # 5.82
        "fw_2.7.0", "iscope_2.7.0", "2597",  # 5.97
        "fw_3.0.0", "iscope_3.0.0", "2645",  # 6.45
        "fw_3.0.1", "iscope_3.0.1", "2658",  # 6.58
        "fw_3.0.2", "iscope_3.0.2", "2670",  # 6.70
        "fw_3.1.0", "iscope_3.1.0", "2706",  # 7.06
        "fw_3.1.1", "iscope_3.1.1", "2718",  # 7.18
        "fw_3.1.2", "iscope_3.1.2", "2732",  # 7.32
        "seestar_v2.6.4", "seestar_v2.7.0", "seestar_v3.",
    ]
    if args.firmware and any(m in args.firmware for m in WEDGE_KNOWN_BAD):
        print("=" * 70)
        print("! KNOWN-BAD FIRMWARE DETECTED !")
        print("=" * 70)
        print(f"Target: {args.firmware}")
        print()
        print("This firmware wedges the BCM43456 WiFi chip with a persistent")
        print("HT Avail timeout on this S50. Recovery requires a full")
        print("rkdeveloptool reflash (~75 min).")
        print()
        print("Known-safe endpoint: fw_2.6.1 (app 5.50).")
        print("See UPGRADE_PROBLEM_SUMMARY.md for full details.")
        print()
        print("Pass --force to proceed anyway (NOT RECOMMENDED).")
        if not args.force:
            sys.exit(1)
        else:
            print("[!] --force override accepted. Proceeding.")
        print("=" * 70)
        print()

    # Display warnings
    print("=" * 70)
    print("SEESTAR FIRMWARE FLASH TOOL")
    print("=" * 70)
    print("\nWARNING: This tool bypasses normal firmware update checks!")
    print("- May brick your device if firmware is incompatible")
    print("- May void your warranty")
    print("- No official support")
    print("- Use at your own risk")
    print("\nPress Ctrl+C now to abort, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n[*] Aborted by user")
        sys.exit(1)

    # Determine firmware file and platform
    firmware_file = args.firmware
    is_x64 = False

    if args.auto or not firmware_file:
        # Auto-detect platform and check device readiness
        print("\n" + "=" * 70)
        print("CHECKING DEVICE STATUS")
        print("=" * 70)

        platform, is_ready, reason = check_device_ready_for_update(args.host, key_path=args.key)

        # Check safety conditions
        if not is_ready:
            print(f"\n{'='*70}")
            print(f"DEVICE NOT READY FOR UPDATE")
            print(f"{'='*70}")
            print(f"Reason: {reason}")
            print(f"\nThe Android app enforces these safety checks:")
            print(f"  - Battery must be ≥20% OR device must be charging")
            print(f"\nRecommendations:")
            print(f"  - Charge the device to at least 20%")
            print(f"  - OR plug in charging cable during update")
            print(f"  - OR use --force to bypass safety checks (NOT RECOMMENDED)")
            print(f"{'='*70}\n")

            if not args.force:
                sys.exit(1)
            else:
                print(f"[!] WARNING: Safety checks bypassed with --force")
                print(f"[!] Update may fail if device loses power!\n")

        # Select firmware based on platform
        if platform == 1:
            firmware_file = "iscope_64"
            is_x64 = True
            print(f"\n[*] Selected firmware: {firmware_file}")
        else:
            firmware_file = "iscope"
            is_x64 = False
            print(f"\n[*] Selected firmware: {firmware_file}")

        # Check if file exists
        if not Path(firmware_file).exists():
            print(f"[!] Error: Firmware file '{firmware_file}' not found")
            print(f"[!] Firmware typically comes from firmware/decompiled/seestar_vX.Y.Z_decompiled/resources/assets/iscope")
            sys.exit(1)
    else:
        # Manual firmware file - detect if x64 from filename
        if '64' in firmware_file:
            is_x64 = True

        # Still check battery even when manually specifying firmware
        print("\n" + "=" * 70)
        print("CHECKING DEVICE STATUS")
        print("=" * 70)

        _, is_ready, reason = check_device_ready_for_update(args.host, key_path=args.key)

        if not is_ready and not args.force:
            print(f"\n[!] Device not ready: {reason}")
            print(f"[!] Use --force to bypass (not recommended)")
            sys.exit(1)

    # Capture pre-upgrade firmware_ver_int so we can detect reboot by CHANGE.
    pre_upgrade_fw = None
    try:
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _sock.settimeout(5)
        _sock.connect((args.host, 4700))
        _ve = read_initial_version(_sock, timeout=2.0)
        _sock.close()
        if _ve is not None:
            pre_upgrade_fw = _ve.get("firmware_ver_int")
            print(f"[+] Pre-upgrade firmware: {_ve.get('firmware_ver_string')} ({pre_upgrade_fw})")
    except Exception as _e:
        print(f"[*] Could not read pre-upgrade firmware_ver_int: {_e}")

    # Create flasher
    flasher = SeestarFirmwareFlasher(args.host, firmware_file, is_x64=is_x64)

    # Run flash process
    if args.dry_run:
        print("\n[*] DRY RUN MODE - Will not transfer firmware")
        flasher.validate_firmware_file()
        flasher.connect_sockets()
        flasher.send_begin_recv()
        flasher.disconnect()
    else:
        success = flasher.flash_firmware()
        if success and args.set_country and args.set_country.lower() not in ('none', 'no', 'off'):
            # Post-upgrade: send set_wifi_country as the vendor APK does via
            # BLE's ble_connect wifi_country field. Runs as soon as the device
            # is reachable on port 4700 again, aiming to beat any sound-33
            # retry-loop escalation.
            post_ok = post_upgrade_set_wifi_country(args.host, args.set_country,
                                                    max_wait=args.post_upgrade_wait,
                                                    pre_upgrade_fw=pre_upgrade_fw)
            if not post_ok:
                print(f"\n[!] set_wifi_country post-step failed or timed out.")
                print(f"    Retry manually once reachable:")
                print(f"    python3 tools/set_wifi_country.py --host {args.host} --country {args.set_country}")
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
