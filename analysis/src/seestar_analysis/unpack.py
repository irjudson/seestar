"""
Unpack APK/XAPK files and decompile with jadx.
"""

import zipfile
import shutil
import subprocess
from pathlib import Path

JADX = Path(__file__).parent.parent.parent / "jadx" / "bin" / "jadx"
APKS_DIR = Path(__file__).parent.parent.parent.parent  # Seestar/
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def find_apks(seestar_dir: Path) -> list[tuple[str, Path]]:
    """Find all Seestar APK/XAPK files, return (version, path) sorted by version."""
    results = []
    all_files = list(seestar_dir.glob("Seestar*.apk")) + list(seestar_dir.glob("Seestar*.xapk"))
    seen_names = set()
    for f in all_files:
        name = f.name
        # Extract version from filename
        version = None
        for part in name.replace("Seestar_v", "").replace("Seestarv", "").split("_"):
            if part[0].isdigit():
                version = part.split(".apk")[0].split(".xapk")[0]
                break
        if version and version not in seen_names:
            seen_names.add(version)
            results.append((version, f))

    results.sort(key=lambda x: [int(p) for p in x[0].split(".")])
    return results


def extract_apk_from_xapk(xapk_path: Path, work_dir: Path) -> Path:
    """Extract the main APK from an XAPK bundle."""
    work_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(xapk_path, 'r') as zf:
        names = zf.namelist()
        # Find the main APK (largest .apk that matches package name)
        apk_files = [n for n in names if n.endswith('.apk') and 'com.zwo.seestar' in n]
        if not apk_files:
            apk_files = [n for n in names if n.endswith('.apk') and '/' not in n]
        if not apk_files:
            apk_files = [n for n in names if n.endswith('.apk')]
        if not apk_files:
            raise ValueError(f"No APK found in {xapk_path}")
        # Pick the largest one
        main_apk = max(apk_files, key=lambda n: zf.getinfo(n).file_size)
        apk_path = work_dir / Path(main_apk).name
        with zf.open(main_apk) as src, open(apk_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    return apk_path


def decompile(apk_path: Path, out_dir: Path, jobs: int = 4) -> Path:
    """Run jadx to decompile an APK into out_dir/sources."""
    sources_dir = out_dir / "sources"
    if sources_dir.exists() and any(sources_dir.rglob("*.java")):
        return sources_dir

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(JADX),
        "--output-dir", str(out_dir),
        "--threads-count", str(jobs),
        "--no-res",           # skip resources (faster)
        "--show-bad-code",
        str(apk_path),
    ]
    print(f"  Running jadx on {apk_path.name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and not sources_dir.exists():
        raise RuntimeError(f"jadx failed: {result.stderr[:500]}")
    return sources_dir


def unpack_version(version: str, apk_path: Path, force: bool = False) -> Path:
    """Full unpack pipeline: XAPK → APK → jadx → sources dir."""
    out_dir = OUTPUT_DIR / f"v{version}"
    sources_dir = out_dir / "sources"

    if sources_dir.exists() and any(sources_dir.rglob("*.java")) and not force:
        print(f"  [skip] v{version} already decompiled")
        return sources_dir

    work_dir = out_dir / "_work"

    if apk_path.suffix == ".xapk":
        print(f"  Extracting APK from XAPK: {apk_path.name}")
        apk_path = extract_apk_from_xapk(apk_path, work_dir)
    elif apk_path.suffix == ".apk":
        work_dir.mkdir(parents=True, exist_ok=True)
        dest = work_dir / apk_path.name
        if not dest.exists():
            shutil.copy2(apk_path, dest)
        apk_path = dest

    decompile(apk_path, out_dir)

    # Clean up work dir
    shutil.rmtree(work_dir, ignore_errors=True)
    return sources_dir
