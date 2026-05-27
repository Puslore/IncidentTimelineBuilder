from __future__ import annotations

import dataclasses
from datetime import datetime, timezone, timedelta
import pytest

from timeline_core.exceptions import (
    InvalidFormatError,
    ParseError,
    TimezoneError,
    ValidationError,
)
from timeline_core.models import LogEvent, LogSource, Timeline
from timeline_core.parsers.nginx_combined import NginxCombinedParser, _parse_timestamp, _classify_level


# ==============================================================================
# Model Tests
# ==============================================================================

def test_log_source_creation() -> None:
    '''
    Test LogSource creation, attribute types, and immutability.
    '''
    source = LogSource(
        name='nginx',
        format='nginx-combined',
        timezone='UTC',
        file_path='tests/fixtures/nginx-access.log',
        filters={'level': 'INFO'},
    )
    assert source.name == 'nginx'
    assert source.format == 'nginx-combined'
    assert source.timezone == 'UTC'
    assert source.file_path == 'tests/fixtures/nginx-access.log'
    assert source.filters == {'level': 'INFO'}

    with pytest.raises(dataclasses.FrozenInstanceError):
        # type: ignore
        source.name = 'new-name'  # type: ignore


def test_log_event_creation() -> None:
    '''
    Test LogEvent creation, attributes, and immutability.
    '''
    dt = datetime(2026, 5, 27, 11, 23, 5, tzinfo=timezone.utc)
    event = LogEvent(
        timestamp=dt,
        source='nginx-access',
        level='INFO',
        message='GET /api/users HTTP/1.1 200 1234',
        metadata={'client': '192.168.1.10'},
        raw_line='raw-line-data',
    )
    assert event.timestamp == dt
    assert event.source == 'nginx-access'
    assert event.level == 'INFO'
    assert event.message == 'GET /api/users HTTP/1.1 200 1234'
    assert event.metadata == {'client': '192.168.1.10'}
    assert event.raw_line == 'raw-line-data'

    with pytest.raises(dataclasses.FrozenInstanceError):
        # type: ignore
        event.level = 'ERROR'  # type: ignore


def test_timeline_creation() -> None:
    '''
    Test Timeline creation, attributes, and immutability.
    '''
    dt1 = datetime(2026, 5, 27, 11, 23, 5, tzinfo=timezone.utc)
    dt2 = datetime(2026, 5, 27, 11, 23, 12, tzinfo=timezone.utc)
    e1 = LogEvent(dt1, 'nginx', 'INFO', 'msg1')
    e2 = LogEvent(dt2, 'nginx', 'ERROR', 'msg2')

    timeline = Timeline(
        events=[e1, e2],
        start_time=dt1,
        end_time=dt2,
        sources=['nginx'],
    )
    assert timeline.events == [e1, e2]
    assert timeline.start_time == dt1
    assert timeline.end_time == dt2
    assert timeline.sources == ['nginx']

    with pytest.raises(dataclasses.FrozenInstanceError):
        # type: ignore
        timeline.start_time = dt2  # type: ignore


# ==============================================================================
# Exception Tests
# ==============================================================================

def test_parse_error() -> None:
    '''
    Test ParseError class fields and string representation.
    '''
    err = ParseError('Failed to parse line', line_number=42, source_name='syslog')
    assert isinstance(err, Exception)
    assert err.line_number == 42
    assert err.source_name == 'syslog'
    assert str(err) == 'Failed to parse line'


def test_invalid_format_error() -> None:
    '''
    Test InvalidFormatError class fields.
    '''
    err = InvalidFormatError('Unsupported format', format_name='unknown-format')
    assert isinstance(err, ValueError)
    assert err.format_name == 'unknown-format'
    assert str(err) == 'Unsupported format'


def test_timezone_error() -> None:
    '''
    Test TimezoneError class fields.
    '''
    err = TimezoneError('Invalid timezone', timezone_value='GMT+99')
    assert isinstance(err, ValueError)
    assert err.timezone_value == 'GMT+99'
    assert str(err) == 'Invalid timezone'


def test_validation_error() -> None:
    '''
    Test ValidationError class fields.
    '''
    err = ValidationError('Validation failed', field_name='timezone')
    assert isinstance(err, Exception)
    assert err.field_name == 'timezone'
    assert str(err) == 'Validation failed'


# ==============================================================================
# NginxCombinedParser Tests
# ==============================================================================

def test_classify_level() -> None:
    '''
    Test that HTTP status codes map correctly to log levels.
    '''
    assert _classify_level(200) == 'INFO'
    assert _classify_level(304) == 'INFO'
    assert _classify_level(400) == 'ERROR'
    assert _classify_level(404) == 'ERROR'
    assert _classify_level(500) == 'ERROR'


def test_parse_timestamp_success() -> None:
    '''
    Test successful parsing of nginx timestamps with offsets.
    '''
    dt = _parse_timestamp('27/May/2026:14:23:05 +0300')
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 27
    assert dt.hour == 14
    assert dt.minute == 23
    assert dt.second == 5
    assert dt.tzinfo == timezone(timedelta(hours=3))

    # Test negative offset
    dt_neg = _parse_timestamp('27/May/2026:14:23:05 -0500')
    assert dt_neg.tzinfo == timezone(timedelta(hours=-5))


def test_parse_timestamp_failures() -> None:
    '''
    Test validation errors during timestamp parsing.
    '''
    # No space between timestamp and offset
    with pytest.raises(ValueError):
        _parse_timestamp('27/May/2026:14:23:05+0300')

    # Invalid timestamp format
    with pytest.raises(ValueError):
        _parse_timestamp('2026-05-27 14:23:05 +0300')


def test_nginx_parser_success_info() -> None:
    '''
    Test successfully parsing an Nginx combined line with INFO status.
    '''
    parser = NginxCombinedParser(source_name='nginx-access')
    line = '192.168.1.10 - alice [27/May/2026:14:23:05 +0300] "GET /api/users HTTP/1.1" 200 1234 "https://example.com" "Mozilla/5.0"'
    event = parser.parse(line, line_number=10)

    assert event.source == 'nginx-access'
    assert event.level == 'INFO'
    assert event.message == 'GET /api/users HTTP/1.1 200 1234'
    assert event.raw_line == line
    assert event.metadata == {
        'client': '192.168.1.10',
        'user': 'alice',
        'referer': 'https://example.com',
    }
    # Check timestamp normalized to target offset
    expected_dt = datetime(2026, 5, 27, 14, 23, 5, tzinfo=timezone(timedelta(hours=3)))
    assert event.timestamp == expected_dt


def test_nginx_parser_success_error() -> None:
    '''
    Test successfully parsing an Nginx combined line with ERROR status (e.g. 500).
    '''
    parser = NginxCombinedParser(source_name='nginx-errors')
    line = '10.0.0.5 - - [27/May/2026:14:23:12 +0300] "POST /api/orders HTTP/1.1" 500 89 "-" "curl/7.88"'
    event = parser.parse(line, line_number=15)

    assert event.source == 'nginx-errors'
    assert event.level == 'ERROR'
    assert event.message == 'POST /api/orders HTTP/1.1 500 89'
    assert event.metadata == {
        'client': '10.0.0.5',
        'user': '-',
        'referer': '-',
    }


def test_nginx_parser_success_malformed_request_field() -> None:
    '''
    Test parser fallback when request field is not standard "METHOD path protocol".
    '''
    parser = NginxCombinedParser(source_name='nginx')
    # Request field is just "invalid-request-string"
    line = '192.168.1.10 - alice [27/May/2026:14:23:05 +0300] "invalid-request-string" 200 1234 "https://example.com" "Mozilla/5.0"'
    event = parser.parse(line, line_number=20)

    assert event.message == 'invalid-request-string   200 1234'


def test_nginx_parser_failure_invalid_regex() -> None:
    '''
    Test that lines not matching nginx combined format raise ParseError.
    '''
    parser = NginxCombinedParser(source_name='nginx')
    line = '192.168.1.10 invalid line content'
    with pytest.raises(ParseError) as exc_info:
        parser.parse(line, line_number=5)

    assert exc_info.value.line_number == 5
    assert exc_info.value.source_name == 'nginx'
    assert 'does not match nginx combined format' in str(exc_info.value)


def test_nginx_parser_failure_bad_timestamp_format() -> None:
    '''
    Test that lines with invalid timestamp values raise ParseError.
    '''
    parser = NginxCombinedParser(source_name='nginx')
    # Timestamp lacks date/time parts but regex matches: [bad-timestamp]
    line = '192.168.1.10 - alice [bad-timestamp] "GET /api/users HTTP/1.1" 200 1234 "https://example.com" "Mozilla/5.0"'
    with pytest.raises(ParseError) as exc_info:
        parser.parse(line, line_number=7)

    assert exc_info.value.line_number == 7
    assert exc_info.value.source_name == 'nginx'
    assert 'Invalid timestamp' in str(exc_info.value)
