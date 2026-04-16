"""
Seestar APK Analysis CLI
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import track

from .unpack import find_apks, unpack_version, OUTPUT_DIR, APKS_DIR
from .extract import extract_all, save, load
from .report import render_version_report, render_comparison, save_report
from .firmware import (
    analyze_firmware, render_firmware_report, render_firmware_comparison,
    save_firmware_data, load_firmware_data,
)

console = Console()

SEESTAR_DIR = APKS_DIR


@click.group()
def cli():
    """Seestar APK analysis toolbox."""
    pass


@cli.command()
@click.option("--dir", "seestar_dir", default=str(SEESTAR_DIR), help="Directory containing APKs")
def list_apks(seestar_dir):
    """List all available Seestar APK versions."""
    apks = find_apks(Path(seestar_dir))
    table = Table(title="Available Seestar APKs")
    table.add_column("Version", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Size", justify="right")
    table.add_column("Decompiled", style="green")
    for version, path in apks:
        size = f"{path.stat().st_size / 1024 / 1024:.0f} MB"
        decompiled = "✓" if (OUTPUT_DIR / f"v{version}" / "sources").exists() else ""
        table.add_row(version, path.name, size, decompiled)
    console.print(table)


@cli.command()
@click.argument("version", required=False)
@click.option("--all", "all_versions", is_flag=True, help="Decompile all versions")
@click.option("--dir", "seestar_dir", default=str(SEESTAR_DIR))
@click.option("--force", is_flag=True, help="Re-decompile even if already done")
def decompile(version, all_versions, seestar_dir, force):
    """Decompile APK(s) with jadx."""
    apks = find_apks(Path(seestar_dir))
    if all_versions:
        targets = apks
    elif version:
        targets = [(v, p) for v, p in apks if v == version]
        if not targets:
            console.print(f"[red]Version {version} not found[/red]")
            return
    else:
        console.print("[red]Specify a version or --all[/red]")
        return

    for ver, path in targets:
        console.print(f"\n[cyan]Decompiling v{ver}...[/cyan]")
        try:
            sources = unpack_version(ver, path, force=force)
            console.print(f"  [green]Done:[/green] {sources}")
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")


@cli.command()
@click.argument("version", required=False)
@click.option("--all", "all_versions", is_flag=True)
@click.option("--dir", "seestar_dir", default=str(SEESTAR_DIR))
def analyze(version, all_versions, seestar_dir):
    """Extract data and generate markdown report for version(s)."""
    apks = find_apks(Path(seestar_dir))
    if all_versions:
        targets = apks
    elif version:
        targets = [(v, p) for v, p in apks if v == version]
        if not targets:
            # Try loading from already-decompiled output
            out = OUTPUT_DIR / f"v{version}" / "sources"
            if out.exists():
                targets = [(version, None)]
            else:
                console.print(f"[red]Version {version} not found[/red]")
                return
    else:
        console.print("[red]Specify a version or --all[/red]")
        return

    for ver, _ in targets:
        sources = OUTPUT_DIR / f"v{ver}" / "sources"
        if not sources.exists():
            console.print(f"[yellow]v{ver}: not decompiled yet, run decompile first[/yellow]")
            continue

        console.print(f"\n[cyan]Analyzing v{ver}...[/cyan]")
        try:
            data = extract_all(ver, sources)
            save(data, OUTPUT_DIR / f"v{ver}")
            report = render_version_report(data)
            save_report(report, OUTPUT_DIR / f"v{ver}" / "report.md")
            console.print(f"  Commands: {len(data.commands)}, Endpoints: {len(data.endpoints)}")
            if data.info.firmware_version:
                console.print(f"  Firmware target: {data.info.firmware_version}")
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")
            import traceback; traceback.print_exc()


@cli.command()
@click.argument("version1")
@click.argument("version2")
def compare(version1, version2):
    """Compare two versions and show what changed."""
    d1 = load(version1, OUTPUT_DIR)
    d2 = load(version2, OUTPUT_DIR)

    if not d1:
        console.print(f"[red]v{version1} not analyzed yet. Run: analyze {version1}[/red]")
        return
    if not d2:
        console.print(f"[red]v{version2} not analyzed yet. Run: analyze {version2}[/red]")
        return

    report = render_comparison(d1, d2)
    out_path = OUTPUT_DIR / f"compare_v{version1}_vs_v{version2}.md"
    save_report(report, out_path)
    console.print(report)


@cli.command()
@click.option("--dir", "seestar_dir", default=str(SEESTAR_DIR))
@click.option("--force-decompile", is_flag=True)
def run_all(seestar_dir, force_decompile):
    """Decompile + analyze all versions, then compare each consecutive pair."""
    apks = find_apks(Path(seestar_dir))
    console.print(f"[bold]Found {len(apks)} APK versions[/bold]\n")

    # Decompile all
    for ver, path in apks:
        console.print(f"[cyan]Decompiling v{ver}...[/cyan]")
        try:
            unpack_version(ver, path, force=force_decompile)
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")

    # Analyze all
    versions_done = []
    for ver, _ in apks:
        sources = OUTPUT_DIR / f"v{ver}" / "sources"
        if not sources.exists():
            console.print(f"[yellow]Skipping v{ver} (no sources)[/yellow]")
            continue
        console.print(f"[cyan]Analyzing v{ver}...[/cyan]")
        try:
            data = extract_all(ver, sources)
            save(data, OUTPUT_DIR / f"v{ver}")
            report = render_version_report(data)
            save_report(report, OUTPUT_DIR / f"v{ver}" / "report.md")
            versions_done.append(ver)
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")

    # Compare consecutive pairs
    console.print("\n[bold]Generating comparison reports...[/bold]")
    for i in range(len(versions_done) - 1):
        v1, v2 = versions_done[i], versions_done[i + 1]
        d1, d2 = load(v1, OUTPUT_DIR), load(v2, OUTPUT_DIR)
        if d1 and d2:
            report = render_comparison(d1, d2)
            save_report(report, OUTPUT_DIR / f"compare_v{v1}_vs_v{v2}.md")

    console.print(f"\n[green]Done! Reports in {OUTPUT_DIR}[/green]")


@cli.command()
@click.argument("version", required=False)
@click.option("--all", "all_versions", is_flag=True)
@click.option("--dir", "seestar_dir", default=str(SEESTAR_DIR))
def analyze_fw(version, all_versions, seestar_dir):
    """Extract and analyze embedded firmware packages from APK(s)."""
    apks = find_apks(Path(seestar_dir))
    work_dir = OUTPUT_DIR / "_fw_work"

    if all_versions:
        targets = apks
    elif version:
        targets = [(v, p) for v, p in apks if v == version]
        if not targets:
            console.print(f"[red]Version {version} not found[/red]")
            return
    else:
        console.print("[red]Specify a version or --all[/red]")
        return

    for ver, path in targets:
        console.print(f"\n[cyan]Extracting firmware from v{ver}...[/cyan]")
        try:
            info = analyze_firmware(ver, path, work_dir)
            save_firmware_data(info, OUTPUT_DIR / f"v{ver}")
            report = render_firmware_report(info)
            rpt_path = OUTPUT_DIR / f"v{ver}" / "firmware_report.md"
            rpt_path.write_text(report)
            console.print(f"  MCU: {info.mcu_firmware or 'unknown'}  |  deb: {info.asiair_deb_version or 'unknown'}")
            console.print(f"  Report: {rpt_path}")
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")
            import traceback; traceback.print_exc()


@cli.command()
@click.argument("version1")
@click.argument("version2")
def compare_fw(version1, version2):
    """Compare firmware packages between two versions."""
    a = load_firmware_data(version1, OUTPUT_DIR)
    b = load_firmware_data(version2, OUTPUT_DIR)
    if not a:
        console.print(f"[red]v{version1} firmware not analyzed. Run: analyze-fw {version1}[/red]")
        return
    if not b:
        console.print(f"[red]v{version2} firmware not analyzed. Run: analyze-fw {version2}[/red]")
        return
    report = render_firmware_comparison(a, b)
    out = OUTPUT_DIR / f"compare_fw_v{version1}_vs_v{version2}.md"
    out.write_text(report)
    console.print(report)
    console.print(f"\n[green]Saved to {out}[/green]")


def main():
    cli()
