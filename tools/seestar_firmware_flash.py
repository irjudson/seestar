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

        # Authenticate with device (firmware 6.45+ requires this)
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

            # Step 5: Wait for update to complete (using mock timer like Android app)
            if not self.wait_for_update_completion():
                print(f"[!] Update wait failed")
                return False

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

    args = parser.parse_args()

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
            print(f"[!] Please build firmware first with build_firmware.sh")
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
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
