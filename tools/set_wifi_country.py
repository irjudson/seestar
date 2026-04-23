#!/usr/bin/env python3
"""
Send set_wifi_country(US) JSON-RPC to a Seestar device over port 4700.

This replicates what the vendor Android APK does when a user navigates to
Settings → WiFi Country → United States. Device-side handler in zwoair_imager
invokes network.sh country US → reload_country("US"), which is the vendor-safe
sequence: stop hostapd → ccode=US to sh_conf.txt → wl country US → autochannel_enabled=1
in AP_5G.conf and AP_2.4G.conf → start hostapd.

Usage:
    python3 set_wifi_country.py --host 10.0.0.1 [--country US]
"""

import argparse
import json
import socket
import sys
import time


def send_jsonrpc(host: str, port: int, method: str, params: dict, cmd_id: int = 1, recv_timeout: float = 8.0) -> dict:
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
        print("[!] No initial Version event (unusual but proceeding)")

    # Send the command.
    cmd = {"id": cmd_id, "method": method, "params": params, "jsonrpc": "2.0"}
    line = json.dumps(cmd) + "\r\n"
    print(f"[*] sending: {json.dumps(cmd)}")
    sock.sendall(line.encode("utf-8"))

    # Read until we see a response with our id.
    sock.settimeout(recv_timeout)
    buf = b""
    start = time.time()
    result = None
    while time.time() - start < recv_timeout:
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
    if result is None:
        print(f"[!] no response for id={cmd_id} within {recv_timeout}s")
        print(f"    raw: {buf.decode('utf-8', errors='replace')!r}")
        return {}
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", required=True, help="Seestar device IP")
    ap.add_argument("--country", default="US", help="ISO-3166-1 alpha-2 country code (default: US)")
    ap.add_argument("--port", type=int, default=4700)
    args = ap.parse_args()

    print(f"=== set_wifi_country on {args.host}:{args.port} → {args.country} ===")
    resp = send_jsonrpc(args.host, args.port, "set_wifi_country",
                        {"country": args.country})
    if not resp:
        sys.exit(1)
    print(f"[+] response: {json.dumps(resp, indent=2)}")
    code = resp.get("code", resp.get("result"))
    if code == 0:
        print(f"[+] set_wifi_country accepted. Device runs reload_country(\"{args.country}\") server-side:")
        print(f"    stop hostapd → ccode={args.country} to sh_conf.txt → wl country {args.country}")
        print(f"    → autochannel_enabled=1 in AP_5G.conf & AP_2.4G.conf → start hostapd")
        print(f"    AP should stabilize within ~5s. Subsequent boots will be clean.")
    else:
        print(f"[!] code/result={code} — command may have failed; inspect response above")
        sys.exit(2)


if __name__ == "__main__":
    main()
