from __future__ import annotations

import json
from datetime import datetime, timezone

from timeline_core.exceptions import ParseError
from timeline_core.models import LogEvent
from timeline_core.parsers.base import BaseParser


class JournaldJsonParser(BaseParser):
    '''
    Parser for journald JSON logs.

    Attributes:
        source_name (str): Name to assign to parsed events.
    '''

    def __init__(self, source_name: str = 'journald') -> None:
        '''
        Initialize JournaldJsonParser.

        Args:
            source_name (str): Name to assign to parsed events.
        '''
        self._source_name = source_name

    def parse(self, line: str, line_number: int = 0) -> LogEvent:
        '''
        Parse a single journald JSON format log line.

        Args:
            line (str): Raw JSON string to parse.
            line_number (int): Position of the event in the source.

        Returns:
            LogEvent: Normalized log event.

        Raises:
            ParseError: If the line is not valid JSON or lacks required fields.
        '''
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ParseError(
                f'Invalid JSON line: {line!r}',
                line_number=line_number,
                source_name=self._source_name,
            ) from exc

        if '__REALTIME_TIMESTAMP' not in data or 'MESSAGE' not in data:
            raise ParseError(
                'Missing required journald fields (__REALTIME_TIMESTAMP or MESSAGE)',
                line_number=line_number,
                source_name=self._source_name,
            )

        try:
            ts_micros = int(data['__REALTIME_TIMESTAMP'])
            dt = datetime.fromtimestamp(ts_micros / 1000000.0, tz=timezone.utc)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ParseError(
                f'Invalid __REALTIME_TIMESTAMP: {data["__REALTIME_TIMESTAMP"]!r}',
                line_number=line_number,
                source_name=self._source_name,
            ) from exc

        # Priority mapping to level
        priority_str = data.get('PRIORITY')
        level = 'INFO'
        if priority_str is not None:
            try:
                priority = int(priority_str)
                if priority <= 3:
                    level = 'ERROR'
                elif priority == 4:
                    level = 'WARNING'
            except ValueError:
                pass

        message = data['MESSAGE']

        metadata: dict[str, str | int] = {}
        if '_HOSTNAME' in data:
            metadata['host'] = data['_HOSTNAME']
        if 'PRIORITY' in data:
            try:
                metadata['priority'] = int(data['PRIORITY'])
            except ValueError:
                pass
        if 'SYSLOG_IDENTIFIER' in data:
            metadata['identifier'] = data['SYSLOG_IDENTIFIER']
        if '_PID' in data:
            try:
                metadata['pid'] = int(data['_PID'])
            except ValueError:
                pass

        return LogEvent(
            timestamp=dt,
            source=self._source_name,
            level=level,
            message=message,
            metadata=metadata,
            raw_line=line,
        )
