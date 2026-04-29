#!/usr/bin/env python3
"""Publish a new Staples WBR deck to the static archive site.

Usage:
    publish.py                  # auto-detect newest deck in wbr_generator/
    publish.py path/to/deck.pdf # specify a deck explicitly
    publish.py --no-push        # commit locally only, don't push to remote
    publish.py --rebuild        # rebuild index.html from existing decks (no copy)

The script copies the deck into ./decks/, regenerates index.html with all
decks listed newest-first, then commits and pushes to the configured remote.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent
DECKS_DIR = SITE_ROOT / "decks"
INDEX_PATH = SITE_ROOT / "index.html"
GENERATOR_DIR = Path.home() / "Documents" / "wbr_generator"

DECK_PATTERN = re.compile(r"staples_wbr_week_(\d{4}-\d{2}-\d{2})\.pdf$", re.IGNORECASE)


def find_latest_generator_deck() -> Path | None:
    if not GENERATOR_DIR.exists():
        return None
    candidates = sorted(GENERATOR_DIR.glob("staples_wbr_week_*.pdf"))
    return candidates[-1] if candidates else None


def parse_week_from_filename(name: str) -> str | None:
    m = DECK_PATTERN.search(name)
    return m.group(1) if m else None


def fmt_week_label(week_iso: str) -> str:
    """Render a week-of date as 'Week of M/D/YY' (Mon → Sun)."""
    start = datetime.strptime(week_iso, "%Y-%m-%d")
    end = start + timedelta(days=6)
    if start.year == end.year:
        return f"Week of {start.strftime('%-m/%-d')}–{end.strftime('%-m/%-d/%y')}"
    return f"Week of {start.strftime('%-m/%-d/%y')}–{end.strftime('%-m/%-d/%y')}"


def collect_decks() -> list[tuple[str, Path]]:
    """Return [(week_iso, pdf_path), ...] sorted newest-first."""
    decks: list[tuple[str, Path]] = []
    for pdf in DECKS_DIR.glob("staples_wbr_week_*.pdf"):
        wk = parse_week_from_filename(pdf.name)
        if wk:
            decks.append((wk, pdf))
    decks.sort(key=lambda t: t[0], reverse=True)
    return decks


def render_index(decks: list[tuple[str, Path]]) -> str:
    """Render index.html with the list of decks."""
    rows: list[str] = []
    for i, (wk, pdf) in enumerate(decks):
        label = fmt_week_label(wk)
        href = f"decks/{pdf.name}"
        size_kb = pdf.stat().st_size / 1024
        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        latest_badge = '<span class="badge">Latest</span>' if i == 0 else ""
        mtime = datetime.fromtimestamp(pdf.stat().st_mtime).strftime("%b %-d, %Y")
        rows.append(f"""        <tr>
          <td class="week-cell">
            <a href="{href}" class="deck-link">{label}</a>
            {latest_badge}
          </td>
          <td class="meta">Published {mtime}</td>
          <td class="meta size">{size_str}</td>
          <td class="actions">
            <a href="{href}" class="btn btn-primary" target="_blank" rel="noopener">View</a>
            <a href="{href}" class="btn" download>Download</a>
          </td>
        </tr>""")

    rows_html = "\n".join(rows) if rows else """        <tr><td colspan="4" class="empty">No decks published yet.</td></tr>"""
    last_updated = datetime.now().strftime("%b %-d, %Y at %-I:%M %p")
    deck_count = len(decks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Staples WBR Archive</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif;
    background: #f8fafc;
    color: #0f172a;
    line-height: 1.5;
    min-height: 100vh;
  }}
  .container {{ max-width: 980px; margin: 0 auto; padding: 48px 24px 80px; }}

  header {{
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 24px;
    margin-bottom: 32px;
  }}
  .eyebrow {{
    color: #64748b; font-size: 12px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 6px;
  }}
  h1 {{
    font-size: 32px; font-weight: 700; color: #0f172a;
    margin-bottom: 8px; letter-spacing: -0.5px;
  }}
  .subtitle {{
    color: #475569; font-size: 15px; max-width: 640px;
  }}
  .stats {{
    display: flex; gap: 24px; margin-top: 20px;
    color: #64748b; font-size: 13px;
  }}
  .stats strong {{ color: #0f172a; }}

  table {{
    width: 100%; border-collapse: collapse;
    background: #fff; border-radius: 10px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    overflow: hidden;
  }}
  th, td {{ padding: 16px 20px; text-align: left; border-bottom: 1px solid #f1f5f9; }}
  tbody tr:last-child td {{ border-bottom: 0; }}
  tbody tr:hover {{ background: #f8fafc; }}
  th {{
    background: #f8fafc; color: #475569; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600;
  }}
  .week-cell {{ font-size: 16px; }}
  .deck-link {{
    color: #0f172a; font-weight: 600; text-decoration: none;
  }}
  .deck-link:hover {{ color: #ef2a39; }}
  .meta {{ color: #64748b; font-size: 13px; }}
  .meta.size {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .actions {{ text-align: right; white-space: nowrap; }}
  .empty {{ text-align: center; color: #94a3b8; padding: 48px 0; font-style: italic; }}

  .badge {{
    display: inline-block; margin-left: 8px;
    background: #fee2e2; color: #b91c1c;
    font-size: 11px; font-weight: 700;
    padding: 2px 8px; border-radius: 999px;
    text-transform: uppercase; letter-spacing: 0.5px;
    vertical-align: middle;
  }}
  .btn {{
    display: inline-block; padding: 6px 14px;
    border-radius: 6px; font-size: 13px; font-weight: 600;
    text-decoration: none; border: 1px solid #cbd5e1;
    color: #334155; background: #fff;
    margin-left: 6px; transition: all .15s;
  }}
  .btn:hover {{ background: #f1f5f9; }}
  .btn-primary {{
    background: #0f172a; color: #fff; border-color: #0f172a;
  }}
  .btn-primary:hover {{ background: #1e293b; }}

  footer {{
    margin-top: 32px; padding-top: 20px;
    border-top: 1px solid #e2e8f0;
    color: #94a3b8; font-size: 12px;
    text-align: center;
  }}
  footer a {{ color: #64748b; }}

  @media (max-width: 640px) {{
    .container {{ padding: 24px 16px 48px; }}
    h1 {{ font-size: 24px; }}
    th:nth-child(2), td:nth-child(2),
    th:nth-child(3), td:nth-child(3) {{ display: none; }}
    .actions .btn:not(.btn-primary) {{ display: none; }}
  }}
</style>
</head>
<body>
  <div class="container">
    <header>
      <div class="eyebrow">DoorDash &times; Staples</div>
      <h1>Weekly Business Review Archive</h1>
      <p class="subtitle">
        Pre-read decks for the Staples WBR. Click any week to open the deck;
        the most recent week is at the top.
      </p>
      <div class="stats">
        <span><strong>{deck_count}</strong> deck{'s' if deck_count != 1 else ''} archived</span>
        <span>Last updated <strong>{last_updated}</strong></span>
      </div>
    </header>

    <table>
      <thead>
        <tr>
          <th>Week</th>
          <th>Published</th>
          <th>Size</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
{rows_html}
      </tbody>
    </table>

    <footer>
      Internal use only &middot; DoorDash Logistics
    </footer>
  </div>
</body>
</html>
"""


def run(cmd: list[str], check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd or SITE_ROOT, check=check, text=True, capture_output=True)


def git_has_changes() -> bool:
    out = run(["git", "status", "--porcelain"]).stdout.strip()
    return bool(out)


def has_remote() -> bool:
    out = run(["git", "remote"], check=False).stdout.strip()
    return "origin" in out.split()


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a Staples WBR deck.")
    parser.add_argument("deck", nargs="?", help="Path to deck PDF (defaults to newest in wbr_generator/)")
    parser.add_argument("--no-push", action="store_true", help="Commit locally; do not push")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index from existing decks; do not copy")
    args = parser.parse_args()

    DECKS_DIR.mkdir(parents=True, exist_ok=True)

    week_iso: str | None = None
    if not args.rebuild:
        if args.deck:
            src = Path(args.deck).expanduser().resolve()
        else:
            src = find_latest_generator_deck()
            if not src:
                print(f"No deck found in {GENERATOR_DIR}. Run the WBR generator first or pass a path.")
                return 1

        if not src.exists():
            print(f"Source deck not found: {src}")
            return 1

        week_iso = parse_week_from_filename(src.name)
        if not week_iso:
            print(f"Could not parse week date from filename: {src.name}")
            print("Expected format: staples_wbr_week_YYYY-MM-DD.pdf")
            return 1

        dst = DECKS_DIR / src.name
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            print(f"Deck for week {week_iso} is already up to date.")
        else:
            shutil.copy2(src, dst)
            print(f"Copied {src.name} -> {dst.relative_to(SITE_ROOT)}")

    decks = collect_decks()
    INDEX_PATH.write_text(render_index(decks))
    print(f"Rebuilt index.html with {len(decks)} deck(s)")

    if not (SITE_ROOT / ".git").exists():
        print("\nLocal git repo not initialized yet. Skipping commit/push.")
        print("See README.md for first-time setup steps.")
        return 0

    if not git_has_changes():
        print("Nothing to commit.")
        return 0

    run(["git", "add", "decks", "index.html"])
    label = fmt_week_label(week_iso) if week_iso else "Refresh archive"
    msg = f"Publish {label}" if week_iso else "Rebuild archive index"
    run(["git", "commit", "-m", msg])
    print(f"Committed: {msg}")

    if args.no_push:
        print("Skipping push (--no-push).")
        return 0

    if not has_remote():
        print("\nNo 'origin' remote configured yet — skipping push.")
        print("See README.md for the steps to create the GitHub repo and add the remote.")
        return 0

    push = run(["git", "push"], check=False)
    if push.returncode == 0:
        print("Pushed to origin.")
    else:
        print("Push failed:")
        print(push.stderr)
        return push.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
