from __future__ import annotations

import re
from datetime import datetime
from dateutil import tz
from dateutil import parser as dt_parser

from timeline_core.exceptions import ParseError, TimezoneError
from timeline_core.models import LogEvent
from timeline_core.parsers.base import BaseParser


class CustomRegexParser(BaseParser):
    '''
    A flexible regex-based parser for user-defined log formats.

    Attributes:
        source_name (str): Name to assign to parsed events.
        pattern (str): Regular expression pattern with named groups.
        timezone_str (str): IANA timezone string for timestamps.
    '''

    def __init__(self, source_name: str = 'custom', pattern: str = '', timezone_str: str = 'UTC') -> None:
        '''
        Initialize CustomRegexParser.

        Args:
            source_name (str): Name to assign to parsed events.
            pattern (str): Regular expression pattern with named groups.
            timezone_str (str): IANA timezone string for timestamps.

        Raises:
            TimezoneError: If timezone_str is invalid.
            ValueError: If pattern is empty or invalid regex.
        '''
        self._source_name = source_name
        self._timezone = timezone_str
        self._tz = tz.gettz(timezone_str)
        if self._tz is None:
            raise TimezoneError(f'Invalid timezone: {timezone_str}', timezone_value=timezone_str)

        if not pattern:
            raise ValueError('Custom pattern must be specified')

        try:
            self._pattern = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f'Invalid regex pattern: {pattern!r}') from exc

    def parse(self, line: str, line_number: int = 0) -> LogEvent:
        '''
        Parse a single log line using custom regular expression.

        Args:
            line (str): Raw log line to parse.
            line_number (int): Position of the line in the source file.

        Returns:
            LogEvent: Normalized log event.

        Raises:
            ParseError: If the line does not match the regex pattern or lacks timestamp.
        '''
        stripped = line.strip()
        match = self._pattern.match(stripped)
        if not match:
            raise ParseError(
                f'Line does not match custom pattern: {stripped!r}',
                line_number=line_number,
                source_name=self._source_name,
            )

        groups = match.groupdict()

        if 'timestamp' not in groups:
            raise ParseError(
                'Custom pattern does not capture "timestamp" group',
                line_number=line_number,
                source_name=self._source_name,
            )

        raw_ts = groups['timestamp']
        try:
            # Parse datetime using dateutil to handle arbitrary formats
            dt_naive = dt_parser.parse(raw_ts)
            if dt_naive.tzinfo is None:
                dt = dt_naive.replace(tzinfo=self._tz)
            else:
                dt = dt_naive
        except (ValueError, OverflowError) as exc:
            raise ParseError(
                f'Invalid timestamp value: {raw_ts!r}',
                line_number=line_number,
                source_name=self._source_name,
            ) from exc

        # Level: default to INFO, normalize to uppercase
        raw_level = groups.get('level')
        if raw_level:
            level = raw_level.strip().upper()
        else:
            level = 'INFO'

        message = groups.get('message', stripped)

        # Any extra captured groups are added to metadata
        metadata: dict[str, str | int] = {}
        for key, val in groups.items():
            if key not in ('timestamp', 'level', 'message') and val is not None:
                metadata[key] = val

        return LogEvent(
            timestamp=dt,
            source=self._source_name,
            level=level,
            message=message,
            metadata=metadata,
            raw_line=line,
        )
