from __future__ import annotations

import re
from datetime import datetime, timezone
from dateutil import tz

from timeline_core.exceptions import ParseError, TimezoneError
from timeline_core.models import LogEvent
from timeline_core.parsers.base import BaseParser

_SYSLOG_RE = re.compile(
    r'^(?P<month>[A-Z][a-z]{2})\s+'
    r'(?P<day>\d+)\s+'
    r'(?P<time>\d{2}:\d{2}:\d{2})\s+'
    r'(?P<host>\S+)\s+'
    r'(?P<process>[a-zA-Z0-9_\-\.]+)'
    r'(?:\[(?P<pid>\d+)\])?:\s+'
    r'(?P<message>.+)$'
)

_MONTHS = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}


class SyslogParser(BaseParser):
    '''
    Parser for standard syslog format logs.

    Attributes:
        source_name (str): Name to assign to parsed events.
        timezone_str (str): IANA timezone string for timestamps.
    '''

    def __init__(self, source_name: str = 'syslog', timezone_str: str = 'UTC') -> None:
        '''
        Initialize SyslogParser.

        Args:
            source_name (str): Name to assign to parsed events.
            timezone_str (str): IANA timezone string for timestamps.

        Raises:
            TimezoneError: If timezone_str is invalid.
        '''
        self._source_name = source_name
        self._timezone = timezone_str
        self._tz = tz.gettz(timezone_str)
        if self._tz is None:
            raise TimezoneError(f'Invalid timezone: {timezone_str}', timezone_value=timezone_str)

    def parse(self, line: str, line_number: int = 0) -> LogEvent:
        '''
        Parse a single syslog format log line.

        Args:
            line (str): Raw log line to parse.
            line_number (int): Position of the line in the source file.

        Returns:
            LogEvent: Normalized log event.

        Raises:
            ParseError: If the line does not match syslog format.
        '''
        stripped = line.strip()
        match = _SYSLOG_RE.match(stripped)
        if not match:
            raise ParseError(
                f'Line does not match syslog format: {stripped!r}',
                line_number=line_number,
                source_name=self._source_name,
            )

        groups = match.groupdict()
        month = _MONTHS.get(groups['month'])
        if month is None:
            raise ParseError(
                f'Invalid syslog month: {groups["month"]!r}',
                line_number=line_number,
                source_name=self._source_name,
            )

        day = int(groups['day'])
        time_parts = groups['time'].split(':')
        hour, minute, second = map(int, time_parts)

        # Default to year 2026 for deterministic parsing
        year = 2026

        try:
            dt_naive = datetime(year, month, day, hour, minute, second)
            dt = dt_naive.replace(tzinfo=self._tz)
        except ValueError as exc:
            raise ParseError(
                f'Invalid date/time value: {exc}',
                line_number=line_number,
                source_name=self._source_name,
            ) from exc

        msg = groups['message']
        # Strip kernel timestamp if present
        msg_clean = re.sub(r'^\[\s*\d+\.\d+\]\s*', '', msg)

        # Classify level
        msg_lower = msg_clean.lower()
        if 'kill' in msg_lower or 'out of memory' in msg_lower:
            level = 'FATAL'
        elif any(w in msg_lower for w in ('error', 'failed', 'fail', 'unable')):
            level = 'ERROR'
        else:
            level = 'INFO'

        metadata: dict[str, str | int] = {
            'host': groups['host'],
            'process': groups['process'],
        }
        if groups['pid']:
            metadata['pid'] = int(groups['pid'])

        return LogEvent(
            timestamp=dt,
            source=self._source_name,
            level=level,
            message=msg_clean,
            metadata=metadata,
            raw_line=line,
        )
