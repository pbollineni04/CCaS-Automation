"""
bulk_upload.py — CLI entry point for Five9 Prompt Bulk Upload

Usage:
    python bulk_upload.py --manifest prompts.csv --wav-dir ./wavs [--dry-run]
                          [--domain api.five9.com] [--username USER] [--password PASS]

Credentials fall back to .env / env vars: FIVE9_USERNAME, FIVE9_PASSWORD, FIVE9_DOMAIN
"""

import os
import sys

import click
from dotenv import load_dotenv

from five9_prompts import Five9PromptClient, bulk_upload, OperationResult

load_dotenv()

ACTION_COLORS = {
    "created": "green",
    "updated": "yellow",
    "skipped": "cyan",
    "deleted": "magenta",
    "failed": "red",
}


def _print_results_table(results: list[OperationResult]) -> None:
    col_widths = {
        "name": max(len("Name"), max((len(r.name) for r in results), default=0)),
        "type": max(len("Type"), max((len(r.prompt_type) for r in results), default=0)),
        "action": max(len("Action"), max((len(r.action) for r in results), default=0)),
        "error": max(len("Error"), max((len(r.error or "") for r in results), default=0)),
    }

    header = (
        f"{'Name':<{col_widths['name']}}  "
        f"{'Type':<{col_widths['type']}}  "
        f"{'Action':<{col_widths['action']}}  "
        f"{'Error':<{col_widths['error']}}"
    )
    separator = "-" * len(header)
    click.echo(separator)
    click.echo(header)
    click.echo(separator)

    for r in results:
        color = ACTION_COLORS.get(r.action.split()[0] if r.action else "", "white")
        line = (
            f"{r.name:<{col_widths['name']}}  "
            f"{r.prompt_type:<{col_widths['type']}}  "
            f"{r.action:<{col_widths['action']}}  "
            f"{r.error or '':<{col_widths['error']}}"
        )
        click.secho(line, fg=color)

    click.echo(separator)


@click.command()
@click.option("--manifest", required=True, type=click.Path(exists=True), help="Path to CSV manifest file")
@click.option("--wav-dir", default=".", show_default=True, help="Base directory for WAV file paths in manifest")
@click.option("--dry-run", is_flag=True, default=False, help="Validate and preview actions without making API calls")
@click.option("--domain", default=None, help="Five9 API domain (env: FIVE9_DOMAIN)")
@click.option("--username", default=None, help="Five9 username (env: FIVE9_USERNAME)")
@click.option("--password", default=None, help="Five9 password (env: FIVE9_PASSWORD)")
def main(manifest, wav_dir, dry_run, domain, username, password):
    """Bulk upload or update Five9 prompts from a CSV manifest."""

    domain = domain or os.environ.get("FIVE9_DOMAIN", "api.five9.com")
    username = username or os.environ.get("FIVE9_USERNAME")
    password = password or os.environ.get("FIVE9_PASSWORD")

    if not username or not password:
        click.secho(
            "Error: credentials required. Set FIVE9_USERNAME / FIVE9_PASSWORD in .env or pass --username / --password.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    if dry_run:
        click.secho("[DRY RUN] No API calls will be made.", fg="yellow")
        client = None
    else:
        click.echo(f"Connecting to Five9 at {domain}...")
        client = Five9PromptClient(username=username, password=password, domain=domain)

    results = bulk_upload(
        client=client,
        manifest_path=manifest,
        wav_dir=wav_dir,
        dry_run=dry_run,
    )

    click.echo()
    _print_results_table(results)
    click.echo()

    total = len(results)
    failed = sum(1 for r in results if r.action == "failed")
    created = sum(1 for r in results if r.action == "created")
    updated = sum(1 for r in results if r.action == "updated")
    skipped = sum(1 for r in results if r.action == "skipped")

    click.echo(
        f"Summary: {total} total — "
        f"{click.style(str(created) + ' created', fg='green')}, "
        f"{click.style(str(updated) + ' updated', fg='yellow')}, "
        f"{click.style(str(skipped) + ' skipped', fg='cyan')}, "
        f"{click.style(str(failed) + ' failed', fg='red' if failed else 'white')}"
    )

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
