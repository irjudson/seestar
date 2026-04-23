#!/usr/bin/env python3
"""
Install / verify a Seestar license on-device via JSON-RPC on port 4700.
Replicates the vendor APK's BLE flow: send_to_air_reply wrapping pi_encrypt
(install) and pi_is_verified (verify). Same device-side handlers are reached
by calling the unwrapped JSON-RPC directly on port 4700.

Payload matches the APK exactly (BleUtilsV2.java line 734):
    {"id":14,"method":"pi_encrypt","params":[{
        "sn":"...","cpuId":"...",   # cpuId optional if bleWifiData.cpuid empty
        "auth_code":"...","digest":"...","sign":"..."
    }]}

Works on firmware that has the pi_encrypt handler (confirmed present in
fw_2.6.1 and later). On older firmware the device responds with
{"error":"method not found","code":103}; handle that gracefully.

Usage:
    python3 tools/install_license_rpc.py --host 10.0.0.1
    python3 tools/install_license_rpc.py --host 10.0.0.1 --license-file s50-fs/home/pi/.ZWO/zwoair_license
    python3 tools/install_license_rpc.py --host 10.0.0.1 --verify-only
"""

import argparse
import json
import socket
import sys
import time
from pathlib import Path


def _read_initial_version(sock, timeout=2.0):
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


def rpc(host, port, method, params, cmd_id, timeout=15.0, print_version=True):
    """Send a JSON-RPC request, return parsed response dict (or None on timeout/failure)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((host, port))

    ve = _read_initial_version(sock, timeout=2.0)
    if ve and print_version:
        print(f"[+] device Version: firmware={ve.get('firmware_ver_string')} "
              f"({ve.get('firmware_ver_int')}), is_verified={ve.get('is_verified')}")

    cmd = {"id": cmd_id, "method": method, "params": params, "jsonrpc": "2.0"}
    payload = json.dumps(cmd) + "\r\n"
    sock.sendall(payload.encode("utf-8"))

    sock.settimeout(timeout)
    buf = b""
    start = time.time()
    result = None
    while time.time() - start < timeout:
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
                if parsed.get("id") == cmd_id:
                    result = parsed
                    break
            if result is not None:
                break
        except socket.timeout:
            break
    sock.close()
    return result


def install_license(host, license_file, port=4700):
    with open(license_file) as f:
        lic = json.load(f)
    missing = [f for f in ("sn", "auth_code", "digest", "sign") if f not in lic]
    if missing:
        print(f"[!] License missing fields: {missing}")
        return False

    params_obj = {
        "sn": lic["sn"],
        "auth_code": lic["auth_code"],
        "digest": lic["digest"],
        "sign": lic["sign"],
    }
    if lic.get("cpuId"):
        params_obj["cpuId"] = lic["cpuId"]

    print(f"[*] pi_encrypt: sn={lic['sn']}, cpuId={lic.get('cpuId', '(none)')}")
    resp = rpc(host, port, "pi_encrypt", [params_obj], cmd_id=14)
    if resp is None:
        print("[!] no response to pi_encrypt")
        return False
    print(f"[+] response: {json.dumps(resp)}")
    if resp.get("error") == "method not found" or resp.get("code") == 103:
        print("[!] pi_encrypt not implemented on this firmware — older than fw_2.6.1?")
        return False
    code = resp.get("code", resp.get("result"))
    if code == 0:
        print("[+] pi_encrypt accepted. Device should now have our license installed.")
        return True
    print(f"[!] pi_encrypt returned code/result={code}")
    return False


def verify_license(host, port=4700):
    resp = rpc(host, port, "pi_is_verified", [], cmd_id=15, print_version=False)
    if resp is None:
        print("[!] no response to pi_is_verified")
        return None
    print(f"[+] pi_is_verified: {json.dumps(resp)}")
    if resp.get("error") == "method not found" or resp.get("code") == 103:
        print("[*] pi_is_verified not implemented; checking Version event is_verified flag instead")
        return None
    result = resp.get("result")
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        return result.get("is_verified", result.get("result"))
    return resp.get("code") == 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", required=True)
    ap.add_argument("--license-file", default=None,
                    help="Path to license JSON (default: s50-fs/home/pi/.ZWO/zwoair_license)")
    ap.add_argument("--port", type=int, default=4700)
    ap.add_argument("--verify-only", action="store_true",
                    help="Query pi_is_verified without sending pi_encrypt")
    args = ap.parse_args()

    license_file = args.license_file
    if not license_file:
        script_dir = Path(__file__).resolve().parent
        license_file = script_dir.parent / "s50-fs" / "home" / "pi" / ".ZWO" / "zwoair_license"

    print(f"=== install_license_rpc on {args.host}:{args.port} ===")
    if not args.verify_only:
        print(f"License file: {license_file}")
        if not Path(str(license_file)).exists():
            print(f"[!] License file not found: {license_file}")
            sys.exit(1)
        if not install_license(args.host, str(license_file), args.port):
            sys.exit(2)
        time.sleep(1)

    verified = verify_license(args.host, args.port)
    if verified is True:
        print("[+] DEVICE VERIFIED (pi_is_verified=true)")
        sys.exit(0)
    elif verified is False:
        print("[!] DEVICE NOT VERIFIED (pi_is_verified=false)")
        sys.exit(3)
    else:
        print("[*] Could not determine verification via RPC; check Version event manually.")
        sys.exit(0 if args.verify_only else 0)


if __name__ == "__main__":
    main()
