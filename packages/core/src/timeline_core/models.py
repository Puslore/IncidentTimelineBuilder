from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LogSource:
    '''
    Description of a log source to parse.

    Attributes:
        name (str): Human-readable name of the log source.
        format (str): Log format identifier (e.g. 'nginx-combined', 'syslog').
        timezone (str): IANA timezone string for the source timestamps.
        file_path (str): Path to the log file.
        filters (dict): Optional filters for log selection.
    '''

    name: str
    format: str
    timezone: str
    file_path: str
    filters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class LogEvent:
    '''
    A single normalized log event.

    Attributes:
        timestamp (datetime): Event timestamp normalized to UTC.
        source (str): Name of the originating log source.
        level (str): Severity level (e.g. 'INFO', 'ERROR').
        message (str): Human-readable event message.
        metadata (dict): Additional structured data from the log line.
        raw_line (str): Original unparsed log line.
    '''

    timestamp: datetime
    source: str
    level: str
    message: str
    metadata: dict = field(default_factory=dict)
    raw_line: str = ''


@dataclass(frozen=True)
class Timeline:
    '''
    An ordered collection of log events forming a unified timeline.

    Attributes:
        events (list[LogEvent]): Chronologically ordered log events.
        start_time (datetime): Earliest event timestamp (UTC).
        end_time (datetime): Latest event timestamp (UTC).
        sources (list[str]): Names of all contributing log sources.
    '''

    events: list[LogEvent] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    sources: list[str] = field(default_factory=list)
