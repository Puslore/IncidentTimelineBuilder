from __future__ import annotations

import json
import sys
from datetime import timezone
from pathlib import Path
from typing import Any, Optional

import typer
import yaml

from timeline_core import get_parser
from timeline_core.exceptions import ParseError, InvalidFormatError
from timeline_core.models import LogEvent

app = typer.Typer(
    name='timeline-builder',
    help='Build a unified incident timeline from multiple log sources.',
)

# Mapping of file extensions / common names to parser format identifiers.
_FORMAT_ALIASES: dict[str, str] = {
    'nginx': 'nginx-combined',
    'nginx-combined': 'nginx-combined',
    'syslog': 'syslog',
    'journald': 'journald-json',
    'journald-json': 'journald-json',
    'custom': 'custom',
}

_EXT_TO_FORMAT: dict[str, str] = {
    '.json': 'journald-json',
    '.jsonl': 'journald-json',
}


def _resolve_format(fmt: str) -> str:
    '''
    Resolve a user-provided format string to a canonical format name.

    Args:
        fmt (str): User-provided format string (e.g. 'nginx', 'syslog').

    Returns:
        str: Canonical format name for the parser registry.

    Raises:
        InvalidFormatError: If the format is not recognized.
    '''
    canonical = _FORMAT_ALIASES.get(fmt.lower())
    if canonical is None:
        raise InvalidFormatError(
            f'Unknown format: {fmt!r}. '
            f'Supported: {", ".join(sorted(_FORMAT_ALIASES.keys()))}',
            format_name=fmt,
        )
    return canonical


def _guess_format(file_path: Path) -> str | None:
    '''
    Attempt to guess log format from file name or extension.

    Args:
        file_path (Path): Path to the log file.

    Returns:
        str | None: Guessed canonical format name, or None.
    '''
    name_lower = file_path.name.lower()

    if 'nginx' in name_lower:
        return 'nginx-combined'
    if 'syslog' in name_lower:
        return 'syslog'
    if 'journald' in name_lower or 'journal' in name_lower:
        return 'journald-json'

    return _EXT_TO_FORMAT.get(file_path.suffix.lower())


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


def _parse_file(
    file_path: Path,
    fmt: str,
    source_name: str,
    timezone_str: str = 'UTC',
    pattern: str = '',
) -> list[LogEvent]:
    '''
    Parse a single log file and return a list of LogEvent objects.

    Args:
        file_path (Path): Path to the log file.
        fmt (str): Canonical format name (e.g. 'nginx-combined').
        source_name (str): Label to assign to parsed events.
        timezone_str (str): IANA timezone string.
        pattern (str): Regex pattern (only for 'custom' format).

    Returns:
        list[LogEvent]: Parsed events from the file.
    '''
    parser = get_parser(fmt, source_name=source_name, timezone_str=timezone_str, pattern=pattern)
    events: list[LogEvent] = []

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
                events.append(event)
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
                    events.append(event)
                except ParseError:
                    continue

    return events


def _output_timeline(all_events: list[LogEvent]) -> None:
    '''
    Sort events, build stats, and print the JSON timeline to stdout.

    Args:
        all_events (list[LogEvent]): Collected events from all sources.

    Raises:
        typer.Exit: If no events were parsed.
    '''
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


@app.command()
def parse(
    files: list[Path] = typer.Argument(
        ...,
        help='One or more log file paths to parse.',
    ),
    format: Optional[str] = typer.Option(
        None,
        '--format', '-f',
        help=(
            'Log format: nginx-combined, syslog, journald-json, custom. '
            'If omitted, the format is guessed from the file name.'
        ),
    ),
    tz: str = typer.Option(
        'UTC',
        '--timezone', '-tz',
        help='IANA timezone for timestamps (e.g. Europe/Moscow).',
    ),
    pattern: str = typer.Option(
        '',
        '--pattern', '-p',
        help='Regex pattern (required when format is "custom").',
    ),
    source_name: Optional[str] = typer.Option(
        None,
        '--name', '-n',
        help='Source label for events. Defaults to the file name.',
    ),
) -> None:
    '''
    Parse one or more log files directly without a YAML config.

    Examples:

        # Auto-detect format from file name:
        timeline-builder parse /var/log/nginx/access.log

        # Explicit format:
        timeline-builder parse /var/log/syslog --format syslog

        # Multiple files:
        timeline-builder parse access.log syslog.log

        # Custom regex:
        timeline-builder parse app.log -f custom -p '^(?P<timestamp>...)...'
    '''
    all_events: list[LogEvent] = []

    for file_path in files:
        if not file_path.exists():
            typer.echo(f'Warning: file not found: {file_path}, skipping', err=True)
            continue

        # Determine format: explicit flag > auto-detect > error.
        if format is not None:
            try:
                fmt = _resolve_format(format)
            except InvalidFormatError as exc:
                typer.echo(f'Error: {exc}', err=True)
                raise typer.Exit(code=2)
        else:
            fmt_guess = _guess_format(file_path)
            if fmt_guess is None:
                typer.echo(
                    f'Error: cannot auto-detect format for {file_path.name!r}. '
                    f'Use --format to specify it explicitly.',
                    err=True,
                )
                raise typer.Exit(code=2)
            fmt = fmt_guess

        name = source_name or file_path.stem

        try:
            events = _parse_file(file_path, fmt, name, timezone_str=tz, pattern=pattern)
        except InvalidFormatError as exc:
            typer.echo(f'Error: {exc}', err=True)
            raise typer.Exit(code=2)

        all_events.extend(events)
        typer.echo(
            f'Parsed {len(events)} events from {file_path.name} ({fmt})',
            err=True,
        )

    _output_timeline(all_events)


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
        src_pattern = src.get('pattern', '')

        try:
            parser = get_parser(fmt, source_name=name, timezone_str=timezone_str, pattern=src_pattern)
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

        events = _parse_file(file_path, fmt, name, timezone_str=timezone_str, pattern=src_pattern)
        all_events.extend(events)

    _output_timeline(all_events)


if __name__ == '__main__':
    app()
