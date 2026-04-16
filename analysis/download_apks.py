#!/usr/bin/env python3
"""
Download missing Seestar APK versions from APKCombo using a headless browser.
Requires: pip install playwright && playwright install chromium
"""

import os
import glob
import asyncio
from pathlib import Path

DEST = Path("/home/irjudson/Projects/Seestar")

# All known versions on APKCombo (newest to oldest)
ALL_VERSIONS = [
    "3.1.2", "3.1.1", "3.1.0",
    "3.0.2", "3.0.1", "3.0.0",
    "2.7.0", "2.6.4", "2.6.1", "2.6.0", "2.5.0",
    "2.4.1", "2.4.0", "2.3.1", "2.3.0",
    "2.2.1", "2.2.0", "2.1.0", "2.0.0",
    "1.20.2", "1.20.0", "1.19.0", "1.18.0",
]


def already_have(version):
    """Check if we already have an APK/XAPK for this version."""
    patterns = [
        f"*{version}*.apk",
        f"*{version}*.xapk",
    ]
    for pattern in patterns:
        if glob.glob(str(DEST / pattern)):
            return True
    return False


def versions_to_download():
    missing = []
    for ver in ALL_VERSIONS:
        if already_have(ver):
            print(f"[skip] {ver} — already have it")
        else:
            print(f"[need] {ver}")
            missing.append(ver)
    return missing


async def download_version(page, version):
    import base64 as b64mod
    url = f"https://apkcombo.com/seestar/com.zwo.seestar/download/phone-{version}-apk"
    print(f"\n[download] {version} — {url}")

    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    # Wait for JS to render download links
    await page.wait_for_timeout(3000)

    # Get all links with class info
    all_links = await page.eval_on_selector_all("a", "els => els.map(e => ({href: e.href, text: e.innerText.trim(), cls: e.className}))")

    # Find and decode APKCombo /d?u= redirect URLs (base64-encoded direct URLs)
    direct_urls = []
    for l in all_links:
        if '/d?u=' in l['href']:
            try:
                encoded = l['href'].split('/d?u=')[1]
                padded = encoded + '=' * (-len(encoded) % 4)
                decoded = b64mod.b64decode(padded).decode('utf-8', errors='ignore')
                print(f"  Decoded: {decoded[:100]}")
                direct_urls.append(decoded)
            except Exception:
                pass

    # Try wget on decoded direct URL
    for direct in direct_urls:
        ext = '.xapk' if 'xapk' in direct.lower() else '.apk'
        dest_file = DEST / f"Seestar_v{version}{ext}"
        print(f"  Trying wget: {direct[:80]}")
        proc = await asyncio.create_subprocess_exec(
            "wget", "-q", "--show-progress", "-O", str(dest_file), direct
        )
        await proc.wait()
        if dest_file.exists() and dest_file.stat().st_size > 1024 * 1024:
            print(f"[ok] {dest_file.name} ({dest_file.stat().st_size/1024/1024:.0f} MB)")
            return dest_file
        dest_file.unlink(missing_ok=True)

    # Print all download-related links for debugging
    for l in all_links:
        if 'download' in l['href'].lower() or '/d?' in l['href'] or '.apk' in l['href']:
            print(f"  link cls={l['cls'][:30]} -> {l['href'][:100]}")

    # Fall back to click-to-download
    async with page.expect_download(timeout=300000) as download_info:
        clicked = False
        for selector in [
            "a.variant.octs",              # actual download link (base64 redirect)
            "a[href*='/d?u=']",            # APKCombo redirect download URL
            "a.octs",
            ".file-list a.download",
            "a.download",
            ".apk-file a",
            "a.download-btn",
            ".download-start a",
            "a[data-dt='apk']",
            "a:has-text('Download APK')",
            "a:has-text('Download XAPK')",
            "a:has-text('Download')",
        ]:
            try:
                btn = page.locator(selector).first
                cnt = await btn.count()
                if cnt > 0:
                    await btn.click(timeout=10000)
                    clicked = True
                    print(f"  Clicked: {selector}")
                    break
            except Exception:
                continue
        if not clicked:
            raise Exception("No download button found")

    download = await download_info.value
    suggested = download.suggested_filename or f"Seestar_v{version}.xapk"
    dest_file = DEST / f"Seestar_v{version}{Path(suggested).suffix}"
    await download.save_as(dest_file)
    size = dest_file.stat().st_size / (1024 * 1024)
    print(f"[ok] {dest_file.name} ({size:.0f} MB)")
    return dest_file


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("playwright not installed. Run:")
        print("  pip install playwright && playwright install chromium")
        return

    missing = versions_to_download()
    if not missing:
        print("\nAll versions already downloaded.")
        return

    print(f"\nWill download {len(missing)} versions: {', '.join(missing)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        )
        page = await context.new_page()

        failed = []
        for version in missing:
            try:
                await download_version(page, version)
            except Exception as e:
                print(f"[fail] {version} — {e}")
                failed.append(version)

        await browser.close()

    print("\n--- Summary ---")
    print(f"Downloaded: {len(missing) - len(failed)}")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
