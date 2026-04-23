#!/usr/bin/env python3
"""
Request a Seestar S50 license from api.seestar.com/v1/activation.

The Seestar Android app sends RSA-encrypted sn+cpuId to the server,
which responds with {authCode, digest, sign} — the license JSON that
goes to /home/pi/.ZWO/zwoair_license on the device.

Usage:
    python3 get_license.py [--sn SN] [--cpuid CPUID] [--model MODEL] [--out FILE]

Defaults to the known values for SN 77d82606.
"""

import base64
import json
import argparse
import urllib.request
import urllib.parse
import sys

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# RSA public key from ConstantsBase.PUB_KEY (same as device's publickey.pem)
PUB_KEY_B64 = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDRsuHZIML9s8t9wTOOx1RtpmbD"
    "GKurd1rPsv/OrrhQYQXrpuECRdd2KBHQm5N5Nevy17ryrCMSV1Gp4I+VuiNXqtib"
    "jO2KRq/AtsjrWCE7J11d3tjmbRB/mCcpRRRXA1JBpL9xhDuYG4VvqdNM9B328saL"
    "D1vnd/TYKsES7kXm2wIDAQAB"
)

ACTIVATION_URL = "https://api.seestar.com/v1/activation"


def encrypt_sn(value: str) -> str:
    """RSA/ECB/PKCS1Padding encrypt value with PUB_KEY, return Base64."""
    der = base64.b64decode(PUB_KEY_B64)
    pub_key = serialization.load_der_public_key(der, backend=default_backend())
    encrypted = pub_key.encrypt(value.encode(), padding.PKCS1v15())
    return base64.b64encode(encrypted).decode()


def request_activation(sn: str, cpu_id: str, model: str) -> dict:
    """POST to activation endpoint, return parsed response dict."""
    payload = {
        "sn": encrypt_sn(sn),
        "cpuId": encrypt_sn(cpu_id),
        "model": model,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        ACTIVATION_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def build_license(res_data: dict) -> dict:
    """Convert server SignResBean response to device license format."""
    return {
        "sn":        res_data["sn"],
        "cpuId":     res_data.get("cpuId", ""),
        "auth_code": res_data["authCode"],
        "digest":    res_data["digest"],
        "sign":      res_data["sign"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sn",    default="77d82606",        help="Device serial (last 8 hex of /proc/cpuinfo Serial)")
    parser.add_argument("--cpuid", default="2c0927865bd10180", help="Device CPU ID (16-char Rockchip hwid)")
    parser.add_argument("--model", default="S50",              help="Device model string (server accepts: S50, S30, etc.)")
    parser.add_argument("--out",   default=None,               help="Write license JSON to this file (default: stdout)")
    args = parser.parse_args()

    print(f"Requesting license for sn={args.sn} cpuId={args.cpuid} model={args.model}", file=sys.stderr)
    print(f"POST {ACTIVATION_URL}", file=sys.stderr)

    try:
        resp = request_activation(args.sn, args.cpuid, args.model)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Server response code: {resp.get('code', '?')}", file=sys.stderr)

    if resp.get("code") not in (0, 200, "0", "200"):
        print(f"Server returned error: {resp}", file=sys.stderr)
        sys.exit(1)

    data = resp.get("data") or resp  # server nests under "data"
    license_json = build_license(data)
    out_str = json.dumps(license_json)

    if args.out:
        with open(args.out, "w") as f:
            f.write(out_str)
        print(f"License written to: {args.out}", file=sys.stderr)
    else:
        print(out_str)

    # Verify the sign field decrypts back to auth_code (sanity check)
    try:
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
        der = base64.b64decode(PUB_KEY_B64)
        pub_key = serialization.load_der_public_key(der, backend=default_backend())
        nums = pub_key.public_numbers()
        sign_bytes = base64.b64decode(license_json["sign"])
        sign_int = int.from_bytes(sign_bytes, 'big')
        plain_int = pow(sign_int, nums.e, nums.n)
        plain_bytes = plain_int.to_bytes((plain_int.bit_length() + 7) // 8, 'big')
        # Strip PKCS#1 type 1 padding: 01 FF...FF 00 <data>
        if plain_bytes[0:1] == b'\x01':
            idx = plain_bytes.index(b'\x00', 1)
            decrypted_auth = plain_bytes[idx+1:].decode()
            match = decrypted_auth == license_json["auth_code"]
            print(f"Sign verification: {'PASS' if match else 'FAIL'} (decrypted={decrypted_auth})", file=sys.stderr)
    except Exception as e:
        print(f"Sign verification skipped: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
