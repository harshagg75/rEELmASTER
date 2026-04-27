#!/usr/bin/env python3
"""
CLI to ingest raw video clips into the ReelMind library.
Usage: python src/scripts/ingest_clips.py --clips-dir ./clips [--resume] [--dry-run]
"""
import sys
from pathlib import Path

import typer
from loguru import logger
from rich import box
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

# Allow running from project root: python src/scripts/ingest_clips.py
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.ingestion import ClipIngestionAgent
from src.tools.video_analysis import extract_quality_metrics, extract_usable_segments

app = typer.Typer(help="Ingest raw .mp4 clips into the ReelMind Supabase library.")
console = Console()


def _setup_logging() -> None:
    Path("logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level="WARNING", format="{time:HH:mm:ss} | {level:<8} | {message}")
    logger.add("logs/ingest.log", level="DEBUG", rotation="10 MB", retention="7 days")


@app.command()
def main(
    clips_dir: str = typer.Option(..., "--clips-dir", help="Directory containing .mp4 clips"),
    resume: bool = typer.Option(
        False, "--resume", help="Skip clips already indexed in Supabase"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Run analysis but do NOT write to Supabase"
    ),
) -> None:
    _setup_logging()

    if dry_run:
        console.print("\n[bold yellow]DRY RUN -- no data will be written to Supabase[/bold yellow]")

    clips_path = Path(clips_dir)
    if not clips_path.exists():
        console.print(f"[red]ERROR: Directory not found: {clips_dir}[/red]")
        raise typer.Exit(1)

    mp4_files = sorted(clips_path.glob("*.mp4"))
    if not mp4_files:
        console.print(f"[yellow]No .mp4 files found in {clips_dir}[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Found {len(mp4_files)} clip(s) in {clips_dir}[/bold]\n")

    # --resume: load already-indexed IDs to skip
    indexed_ids: set[str] = set()
    if resume and not dry_run:
        try:
            from src.tools.vector_db import VectorDB
            indexed_ids = VectorDB().get_all_clip_ids()
            console.print(f"[dim]Resume mode: {len(indexed_ids)} clip(s) already indexed[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]WARN: Could not load indexed IDs ({e}) -- processing all clips[/yellow]\n")

    agent = ClipIngestionAgent(dry_run=dry_run)

    stats = {"success": 0, "failed": 0, "skipped": 0}
    results: list[dict] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[clip_name]:<30}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(
            "Ingesting…", total=len(mp4_files), clip_name="starting…"
        )

        for clip_path in mp4_files:
            clip_name = clip_path.stem
            progress.update(task, clip_name=clip_name)

            # Skip already-indexed clips
            if clip_name in indexed_ids:
                stats["skipped"] += 1
                results.append(
                    {"name": clip_name, "status": "[dim]skipped[/dim]",
                     "score": "—", "mood": "—", "summary": "Already indexed"}
                )
                progress.advance(task)
                continue

            try:
                # ── Step 1: Video analysis ─────────────────────────────────
                ffprobe_data = extract_quality_metrics(str(clip_path))
                ffprobe_data["usable_segments"] = extract_usable_segments(
                    str(clip_path), quality_metrics=ffprobe_data
                )

                # ── Step 2: Transcription ──────────────────────────────────
                from src.tools.transcription import transcribe_video
                transcript = transcribe_video(str(clip_path))

                # ── Step 3: Claude analysis (+ optional DB write) ──────────
                metadata = agent.run(str(clip_path), ffprobe_data, transcript)

                stats["success"] += 1
                summary = metadata.transcript_summary
                if len(summary) > 55:
                    summary = summary[:55] + "…"
                results.append(
                    {
                        "name": clip_name,
                        "status": "[green]OK[/green]",
                        "score": f"{metadata.quality_score:.1f}",
                        "mood": metadata.mood,
                        "summary": summary,
                    }
                )

            except Exception as e:
                stats["failed"] += 1
                logger.error(f"[IngestCLI] Failed on {clip_name}: {e}")
                err_msg = str(e)
                if len(err_msg) > 55:
                    err_msg = err_msg[:55] + "…"
                results.append(
                    {
                        "name": clip_name,
                        "status": "[red]FAILED[/red]",
                        "score": "—",
                        "mood": "—",
                        "summary": err_msg,
                    }
                )

            progress.advance(task)

    _print_summary(results, stats, dry_run)


def _print_summary(results: list[dict], stats: dict, dry_run: bool) -> None:
    console.print()
    title = "Ingestion Results" + ("  [yellow](DRY RUN)[/yellow]" if dry_run else "")
    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan", show_lines=False)
    table.add_column("Clip",              style="white",   max_width=30)
    table.add_column("Status",            justify="center", min_width=8)
    table.add_column("Score",             justify="right",  min_width=6)
    table.add_column("Mood",              min_width=16)
    table.add_column("Transcript Summary", max_width=55)

    for r in results:
        table.add_row(r["name"], r["status"], r["score"], r["mood"], r["summary"])

    console.print(table)
    console.print(
        f"\n  [bold]Total: {len(results)}[/bold]  "
        f"[green]OK: {stats['success']}[/green]  "
        f"[red]FAILED: {stats['failed']}[/red]  "
        f"[dim]Skipped: {stats['skipped']}[/dim]\n"
    )


if __name__ == "__main__":
    app()
