#!/usr/bin/env python3
"""
Extract S50 (armhf/32-bit) firmware packages from Seestar APKs/XAPKs.

Always prefers assets/iscope (32-bit S50 firmware) over assets/iscope_64
(64-bit ASIAIR variant). This is the correct blob for the RV1126-based S50.

Output: firmware/packages/fw_{version}/ per APK.
"""

import zipfile
import bz2
import tarfile
import io
import re
import shutil
import sys
from pathlib import Path


APKS_DIR = Path(__file__).parent.parent / "apks"
OUT_DIR  = Path(__file__).parent.parent / "firmware" / "packages"

# Prefer 32-bit iscope; fall back to iscope_64 only if no 32-bit blob exists
ASSET_PREFERENCE = [
    "assets/iscope",
    "assets/iscope_64_armeabi_v7a",
    "assets/iscope_64_arm64",
    "assets/iscope_64",
]


def version_from_path(p: Path) -> str:
    """Extract version string from APK filename, e.g. v2.6.4 -> 2.6.4"""
    name = p.stem
    # Handle odd names like Seestarv2.7.0 or Seestar_3.0.0_apkcombo.com
    m = re.search(r'v?(\d+\.\d+[\.\d]*)', name)
    return m.group(1) if m else name


def find_asset(zf: zipfile.ZipFile) -> str | None:
    names = set(zf.namelist())
    for candidate in ASSET_PREFERENCE:
        if candidate in names:
            return candidate
    # Fallback: any top-level assets/iscope* (not a directory)
    for n in sorted(zf.namelist()):
        if re.match(r"assets/iscope[^/]*$", n):
            return n
    return None


def read_asset(apk_path: Path) -> tuple[bytes, str] | tuple[None, None]:
    """Return (raw_bytes, asset_name). Handles plain APK and XAPK bundles."""
    with zipfile.ZipFile(apk_path, 'r') as outer:
        asset = find_asset(outer)
        if asset:
            print(f"  asset: {asset} ({outer.getinfo(asset).file_size // 1024 // 1024}MB)")
            return outer.read(asset), asset

        # XAPK: look inside asset_pack_0.apk
        if "asset_pack_0.apk" in outer.namelist():
            pack_bytes = outer.read("asset_pack_0.apk")
            with zipfile.ZipFile(io.BytesIO(pack_bytes)) as inner:
                asset = find_asset(inner)
                if asset:
                    print(f"  asset: {asset} (in asset_pack_0.apk, {inner.getinfo(asset).file_size // 1024 // 1024}MB)")
                    return inner.read(asset), asset

        # XAPK: look inside com.zwo.seestar.apk
        if "com.zwo.seestar.apk" in outer.namelist():
            main_bytes = outer.read("com.zwo.seestar.apk")
            with zipfile.ZipFile(io.BytesIO(main_bytes)) as inner:
                asset = find_asset(inner)
                if asset:
                    print(f"  asset: {asset} (in com.zwo.seestar.apk, {inner.getinfo(asset).file_size // 1024 // 1024}MB)")
                    return inner.read(asset), asset

    return None, None


def unpack_asset(raw: bytes, out_dir: Path) -> bool:
    """Decompress bzip2 and extract tar into out_dir."""
    try:
        decompressed = bz2.decompress(raw)
    except Exception as e:
        print(f"  ERROR: bzip2 decompress failed: {e}")
        return False
    try:
        with tarfile.open(fileobj=io.BytesIO(decompressed)) as tf:
            tf.extractall(out_dir, filter="data")
        return True
    except Exception as e:
        print(f"  ERROR: tar extract failed: {e}")
        return False


def process_apk(apk_path: Path, force: bool = False) -> bool:
    version = version_from_path(apk_path)
    out_dir = OUT_DIR / f"fw_{version}"

    print(f"\n{apk_path.name}  →  fw_{version}")

    if out_dir.exists() and not force:
        # Check if it has the wrong (64-bit) binaries
        imager = out_dir / "deb-build" / "asiair_armhf" / "home" / "pi" / "ASIAIR" / "bin" / "zwoair_imager"
        if imager.exists():
            import subprocess
            result = subprocess.run(["file", str(imager)], capture_output=True, text=True)
            if "aarch64" in result.stdout:
                print(f"  existing fw has 64-bit binaries — re-extracting")
            elif "ARM" in result.stdout and "32" in result.stdout:
                print(f"  existing fw has 32-bit binaries — OK, skipping")
                return True
            else:
                print(f"  existing fw: {result.stdout.strip()} — skipping")
                return True
        else:
            print(f"  exists (no imager binary found) — re-extracting")

    raw, asset_name = read_asset(apk_path)
    if raw is None:
        print(f"  WARNING: no iscope asset found")
        return False

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    if not unpack_asset(raw, out_dir):
        return False

    # Verify result
    imager = out_dir / "deb-build" / "asiair_armhf" / "home" / "pi" / "ASIAIR" / "bin" / "zwoair_imager"
    if imager.exists():
        import subprocess
        result = subprocess.run(["file", str(imager)], capture_output=True, text=True)
        arch = "aarch64" if "aarch64" in result.stdout else "ARM 32-bit" if "ARM" in result.stdout else "unknown"
        print(f"  zwoair_imager arch: {arch}")
        if "aarch64" in result.stdout:
            print(f"  WARNING: still 64-bit! Check asset selection.")
    else:
        # Older format: apt-based deb, no deb-build tree
        deb = list(out_dir.glob("deb/*.deb"))
        if deb:
            print(f"  apt-based package: {[d.name for d in deb]}")
        else:
            print(f"  (no zwoair_imager — may be very old format)")

    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    apks = sorted(APKS_DIR.glob("*.apk")) + sorted(APKS_DIR.glob("*.xapk"))

    if not apks:
        print(f"No APKs found in {APKS_DIR}")
        sys.exit(1)

    print(f"Extracting S50 (iscope/armhf) firmware from {len(apks)} APKs")
    print(f"Output: {OUT_DIR}")
    if force:
        print("Mode: --force (re-extract all)")

    ok = err = skip = 0
    for apk in apks:
        if process_apk(apk, force=force):
            ok += 1
        else:
            err += 1

    print(f"\nDone: {ok} extracted/ok, {err} errors")
