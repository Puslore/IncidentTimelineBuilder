from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from timeline_core.exceptions import ParseError
from timeline_core.models import LogEvent
from timeline_core.parsers.base import BaseParser

_NGINX_COMBINED_RE = re.compile(
    r'^'
    r'(?P<client>\S+)\s+'           # client IP
    r'(?P<ident>\S+)\s+'            # ident (usually -)
    r'(?P<user>\S+)\s+'             # remote user
    r'\[(?P<timestamp>[^\]]+)\]\s+' # [day/Mon/year:HH:MM:SS +ZZZZ]
    r'"(?P<request>[^"]*)"\s+'      # "METHOD path protocol"
    r'(?P<status>\d{3})\s+'         # status code
    r'(?P<bytes>\S+)\s+'            # bytes sent
    r'"(?P<referer>[^"]*)"\s+'      # referer
    r'"(?P<user_agent>[^"]*)"'      # user agent
    r'$'
)

_NGINX_TS_FORMAT = '%d/%b/%Y:%H:%M:%S'


def _parse_timestamp(raw: str) -> datetime:
    '''
    Parse nginx timestamp string into a timezone-aware datetime.

    The offset portion (e.g. '+0300') is handled manually to ensure
    consistent behaviour across Python versions.

    Args:
        raw (str): Timestamp string like '27/May/2026:14:23:05 +0300'.

    Returns:
        datetime: Timezone-aware datetime object.

    Raises:
        ValueError: If the timestamp cannot be parsed.
    '''
    parts = raw.rsplit(' ', 1)
    if len(parts) != 2:
        raise ValueError(f'Cannot split timestamp and offset: {raw!r}')

    ts_str, offset_str = parts

    dt_naive = datetime.strptime(ts_str, _NGINX_TS_FORMAT)

    sign = 1 if offset_str[0] == '+' else -1
    hours = int(offset_str[1:3])
    minutes = int(offset_str[3:5])
    tz = timezone(timedelta(hours=sign * hours, minutes=sign * minutes))

    return dt_naive.replace(tzinfo=tz)


def _classify_level(status: int) -> str:
    '''
    Map HTTP status code to log severity level.

    Args:
        status (int): HTTP status code.

    Returns:
        str: 'INFO' for 1xx/2xx/3xx, 'ERROR' for 4xx/5xx.
    '''
    if status >= 400:
        return 'ERROR'
    return 'INFO'


class NginxCombinedParser(BaseParser):
    '''
    Parser for the nginx combined log format.

    Attributes:
        source_name (str): Name to assign to parsed events.
    '''

    def __init__(self, source_name: str = 'nginx-combined') -> None:
        '''
        Initialize NginxCombinedParser.

        Args:
            source_name (str): Source label for generated LogEvent instances.
        '''
        self._source_name = source_name

    def parse(self, line: str, line_number: int = 0) -> LogEvent:
        '''
        Parse a single nginx combined format log line.

        Args:
            line (str): Raw log line to parse.
            line_number (int): Position of the line in the source file.

        Returns:
            LogEvent: Normalized log event.

        Raises:
            ParseError: If the line does not match nginx combined format.
        '''
        stripped = line.strip()
        match = _NGINX_COMBINED_RE.match(stripped)
        if not match:
            raise ParseError(
                f'Line does not match nginx combined format: {stripped!r}',
                line_number=line_number,
                source_name=self._source_name,
            )

        groups = match.groupdict()

        try:
            timestamp = _parse_timestamp(groups['timestamp'])
        except (ValueError, IndexError) as exc:
            raise ParseError(
                f'Invalid timestamp: {groups["timestamp"]!r}',
                line_number=line_number,
                source_name=self._source_name,
            ) from exc

        request_parts = groups['request'].split()
        if len(request_parts) == 3:
            method, path, protocol = request_parts
        else:
            method = groups['request']
            path = ''
            protocol = ''

        status = int(groups['status'])
        bytes_sent = groups['bytes']
        level = _classify_level(status)

        message = f'{method} {path} {protocol} {status} {bytes_sent}'

        user = groups['user']
        metadata = {
            'client': groups['client'],
            'user': user,
            'referer': groups['referer'],
        }

        return LogEvent(
            timestamp=timestamp,
            source=self._source_name,
            level=level,
            message=message,
            metadata=metadata,
            raw_line=line,
        )
