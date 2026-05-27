from __future__ import annotations

import json
import sys
from datetime import timezone
from pathlib import Path
from typing import Any

import typer
import yaml

from timeline_core import get_parser
from timeline_core.exceptions import ParseError, InvalidFormatError
from timeline_core.models import LogEvent

app = typer.Typer(
    name='timeline-builder',
    help='Build a unified incident timeline from multiple log sources.',
)


def _event_to_dict(event: LogEvent) -> dict[str, Any]:
    '''
    Convert a LogEvent to a JSON-serializable dictionary.

    Args:
        event (LogEvent): Normalized log event.

    Returns:
        dict[str, Any]: Dictionary ready for JSON serialization.
    '''
    ts_utc = event.timestamp.astimezone(timezone.utc)
    return {
        'timestamp': ts_utc.isoformat(),
        'source': event.source,
        'level': event.level,
        'message': event.message,
        'metadata': event.metadata,
    }


def _build_stats(events: list[LogEvent], timeline: list[dict[str, Any]]) -> dict[str, Any]:
    '''
    Compute summary statistics for a list of events.

    Args:
        events (list[LogEvent]): Sorted list of log events.
        timeline (list[dict[str, Any]]): Serialized timeline entries.

    Returns:
        dict[str, Any]: Statistics dictionary with counts and time range.
    '''
    by_source: dict[str, int] = {}
    by_level: dict[str, int] = {}
    for evt in events:
        by_source[evt.source] = by_source.get(evt.source, 0) + 1
        by_level[evt.level] = by_level.get(evt.level, 0) + 1

    return {
        'total_events': len(events),
        'by_source': by_source,
        'by_level': by_level,
        'time_range': {
            'start': timeline[0]['timestamp'] if timeline else None,
            'end': timeline[-1]['timestamp'] if timeline else None,
        },
    }


@app.command()
def build(
    config: Path = typer.Argument(
        ...,
        help='Path to sources YAML configuration file.',
    ),
) -> None:
    '''
    Build a unified timeline from log sources defined in CONFIG.

    Reads source definitions from a YAML file, parses each log file
    with the appropriate parser, merges events chronologically, and
    writes the resulting timeline as JSON to stdout.
    '''
    if not config.exists():
        typer.echo(f'Error: config file not found: {config}', err=True)
        raise typer.Exit(code=1)

    with open(config, encoding='utf-8') as fh:
        cfg = yaml.safe_load(fh)

    sources = cfg.get('sources', [])
    if not sources:
        typer.echo('Error: no sources defined in config', err=True)
        raise typer.Exit(code=1)

    all_events: list[LogEvent] = []

    for src in sources:
        fmt = src.get('format', '')
        name = src.get('name', fmt)
        timezone_str = src.get('timezone', 'UTC')
        pattern = src.get('pattern', '')

        try:
            parser = get_parser(fmt, source_name=name, timezone_str=timezone_str, pattern=pattern)
        except InvalidFormatError:
            typer.echo(
                f'Warning: unsupported format {fmt!r}, '
                f'skipping source {name!r}',
                err=True,
            )
            continue

        file_path = Path(src.get('file', ''))
        if not file_path.exists():
            if file_path.suffix == '.jsonl':
                fallback_path = file_path.with_suffix('.json')
                if fallback_path.exists():
                    file_path = fallback_path

        if not file_path.exists():
            typer.echo(
                f'Warning: file not found: {file_path}, '
                f'skipping source {name!r}',
                err=True,
            )
            continue

        if fmt == 'journald-json':
            with open(file_path, encoding='utf-8') as fh:
                content = fh.read()

            decoder = json.JSONDecoder()
            pos = 0
            line_num = 1
            while pos < len(content):
                chunk = content[pos:].lstrip()
                if not chunk:
                    break
                pos = len(content) - len(chunk)
                try:
                    obj, idx = decoder.raw_decode(chunk)
                    json_str = json.dumps(obj)
                    event = parser.parse(json_str, line_number=line_num)
                    all_events.append(event)
                    pos += idx
                    line_num += 1
                except Exception:
                    pos += 1
                    line_num += 1
        else:
            with open(file_path, encoding='utf-8') as fh:
                for line_num, raw_line in enumerate(fh, 1):
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    try:
                        event = parser.parse(stripped, line_number=line_num)
                        all_events.append(event)
                    except ParseError:
                        continue

    if not all_events:
        typer.echo('Warning: no events parsed from any source', err=True)
        raise typer.Exit(code=1)

    all_events.sort(key=lambda e: e.timestamp)

    timeline = [_event_to_dict(e) for e in all_events]
    stats = _build_stats(all_events, timeline)

    output = {
        'timeline': timeline,
        'stats': stats,
    }

    typer.echo(json.dumps(output, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    app()
