#!/usr/bin/env python3
"""
Sign Seestar Firmware Package
Based on the firmware signing format discovered
"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
import sys
import os


def create_update_package(
    firmware_payload: bytes,
    private_key_path: str,
    output_path: str
):
    """
    Create a signed firmware update package

    Format:
    - Firmware payload (tar.bz2 data)
    - 128-byte RSA signature (SHA1 + PKCS1v15)
    """

    # --- Load private key ---
    print(f"[*] Loading private key from: {private_key_path}")
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    print(f"[+] Private key loaded successfully")

    # --- Sign firmware payload (SHA1 + RSA, raw signature) ---
    print(f"[*] Signing firmware payload with SHA1 + PKCS1v15...")
    signature = private_key.sign(
        firmware_payload,
        padding.PKCS1v15(),
        hashes.SHA1()
    )

    # --- Sanity check: firmware expects 128-byte signature (1024-bit RSA) ---
    if len(signature) != 128:
        raise ValueError(f"Signature length is {len(signature)} bytes, expected 128 (1024-bit RSA key required)")

    print(f"[+] Signature generated: {len(signature)} bytes")

    # --- Write update package ---
    print(f"[*] Writing signed package to: {output_path}")
    with open(output_path, "wb") as f:
        f.write(firmware_payload)
        f.write(signature)

    print(f"[+] Update package created successfully!")
    print(f"    Payload size : {len(firmware_payload)} bytes")
    print(f"    Signature    : {len(signature)} bytes (appended)")
    print(f"    Total size   : {len(firmware_payload) + len(signature)} bytes")

    return True


def generate_test_keypair(private_key_path: str, public_key_path: str):
    """Generate a test RSA keypair (for testing only - device will reject it)"""

    print(f"[*] Generating 1024-bit RSA test keypair...")
    print(f"[!] WARNING: This is for TESTING only!")
    print(f"[!] Device will reject firmware signed with this key!")

    # Generate 1024-bit RSA key (same size as ZWO uses)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend()
    )

    # Save private key
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"[+] Private key saved: {private_key_path}")

    # Save public key
    public_key = private_key.public_key()
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print(f"[+] Public key saved: {public_key_path}")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Sign Seestar firmware packages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sign firmware with existing private key
  python sign_firmware.py firmware.tar.bz2 private_key.pem -o signed_firmware.bin

  # Generate test keypair (device will reject!)
  python sign_firmware.py --generate-test-key test_private.pem test_public.pem
        """
    )

    parser.add_argument('input', nargs='?', help='Input firmware file (tar.bz2)')
    parser.add_argument('key', nargs='?', help='Private key file (PEM format)')
    parser.add_argument('-o', '--output', help='Output signed firmware file')
    parser.add_argument('--generate-test-key', nargs=2, metavar=('PRIVATE', 'PUBLIC'),
                       help='Generate test RSA keypair (for testing only)')

    args = parser.parse_args()

    # Generate test keypair
    if args.generate_test_key:
        private_path, public_path = args.generate_test_key
        return 0 if generate_test_keypair(private_path, public_path) else 1

    # Sign firmware
    if not args.input or not args.key:
        parser.error("Input firmware and private key required (or use --generate-test-key)")

    if not args.output:
        args.output = args.input.replace('.tar.bz2', '_signed.bin')

    # Read firmware payload
    print(f"[*] Reading firmware payload: {args.input}")
    with open(args.input, 'rb') as f:
        firmware_payload = f.read()
    print(f"[+] Firmware payload: {len(firmware_payload)} bytes")

    # Sign and create package
    success = create_update_package(firmware_payload, args.key, args.output)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
