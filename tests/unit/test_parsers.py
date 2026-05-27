from __future__ import annotations

from datetime import datetime, timezone, timedelta
import pytest

from timeline_core.exceptions import ParseError, TimezoneError, InvalidFormatError
from timeline_core.models import LogEvent
from timeline_core.parsers import get_parser
from timeline_core.parsers.syslog import SyslogParser
from timeline_core.parsers.journald import JournaldJsonParser
from timeline_core.parsers.custom import CustomRegexParser


# ==============================================================================
# Registry and Factory Tests
# ==============================================================================

def test_get_parser_success() -> None:
    '''
    Test get_parser factory returns correct parser instances.
    '''
    p1 = get_parser('nginx-combined', 'nginx-src')
    assert isinstance(p1, type(get_parser('nginx-combined', 'x')))

    p2 = get_parser('syslog', 'syslog-src', timezone_str='Europe/Moscow')
    assert isinstance(p2, SyslogParser)

    p3 = get_parser('journald-json', 'journald-src')
    assert isinstance(p3, JournaldJsonParser)

    p4 = get_parser('custom', 'custom-src', pattern=r'^(?P<timestamp>\S+)\s+(?P<message>.+)$')
    assert isinstance(p4, CustomRegexParser)


def test_get_parser_invalid_format() -> None:
    '''
    Test get_parser raises InvalidFormatError for unsupported formats.
    '''
    with pytest.raises(InvalidFormatError) as exc_info:
        get_parser('unknown-format-123', 'src')
    assert exc_info.value.format_name == 'unknown-format-123'


# ==============================================================================
# SyslogParser Tests
# ==============================================================================

def test_syslog_parser_success_basic() -> None:
    '''
    Test successful parsing of syslog line with PID and standard format.
    '''
    parser = SyslogParser(source_name='syslog', timezone_str='Europe/Moscow')
    line = 'May 27 14:23:01 webhost01 sshd[1234]: Accepted publickey for alice from 192.168.1.10 port 54321 ssh2'
    event = parser.parse(line, line_number=5)

    assert event.source == 'syslog'
    assert event.level == 'INFO'
    assert event.message == 'Accepted publickey for alice from 192.168.1.10 port 54321 ssh2'
    assert event.metadata == {
        'host': 'webhost01',
        'process': 'sshd',
        'pid': 1234,
    }
    expected_dt = datetime(2026, 5, 27, 14, 23, 1, tzinfo=timezone(timedelta(hours=3)))
    assert event.timestamp == expected_dt


def test_syslog_parser_success_no_pid() -> None:
    '''
    Test parsing syslog line without PID and with kernel OOM message.
    '''
    parser = SyslogParser(source_name='syslog', timezone_str='UTC')
    # OOM logs are mapped to FATAL level
    line = 'May 27 14:23:30 webhost01 kernel: [12345.678] Out of memory: Kill process 5678 (java) score 950 or sacrifice child'
    event = parser.parse(line, line_number=10)

    assert event.source == 'syslog'
    assert event.level == 'FATAL'
    # Kernel timestamp must be stripped
    assert event.message == 'Out of memory: Kill process 5678 (java) score 950 or sacrifice child'
    assert event.metadata == {
        'host': 'webhost01',
        'process': 'kernel',
    }
    assert 'pid' not in event.metadata


def test_syslog_parser_level_classification() -> None:
    '''
    Test syslog level classification logic.
    '''
    parser = SyslogParser(source_name='syslog', timezone_str='UTC')

    # ERROR triggers: "error", "failed", "fail", "unable"
    line_err1 = 'May 27 14:23:30 webhost01 systemd[1]: Failed to start app service.'
    assert parser.parse(line_err1).level == 'ERROR'

    line_err2 = 'May 27 14:23:30 webhost01 app[123]: unable to write to stdout'
    assert parser.parse(line_err2).level == 'ERROR'

    # FATAL triggers: "kill", "out of memory"
    line_fatal = 'May 27 14:23:30 webhost01 kernel: Out of memory'
    assert parser.parse(line_fatal).level == 'FATAL'


def test_syslog_parser_invalid_timezone() -> None:
    '''
    Test initialization with invalid timezone raises TimezoneError.
    '''
    with pytest.raises(TimezoneError) as exc_info:
        SyslogParser(timezone_str='Invalid/Zone')
    assert exc_info.value.timezone_value == 'Invalid/Zone'


def test_syslog_parser_failures() -> None:
    '''
    Test syslog parsing failures for malformed lines.
    '''
    parser = SyslogParser(source_name='syslog', timezone_str='UTC')

    # Pattern mismatch
    with pytest.raises(ParseError) as exc_info:
        parser.parse('Invalid syslog line structure', line_number=1)
    assert exc_info.value.line_number == 1

    # Invalid month name
    with pytest.raises(ParseError) as exc_info:
        parser.parse('Xxx 27 14:23:01 webhost01 sshd[1]: test', line_number=2)

    # Invalid day/time values
    with pytest.raises(ParseError) as exc_info:
        parser.parse('May 32 14:23:01 webhost01 sshd[1]: test', line_number=3)


# ==============================================================================
# JournaldJsonParser Tests
# ==============================================================================

def test_journald_parser_success() -> None:
    '''
    Test journald JSON parsing with priority mapping and microsecond timestamps.
    '''
    parser = JournaldJsonParser(source_name='journald')
    line = '{"__REALTIME_TIMESTAMP": "1779967382500000", "_HOSTNAME": "webhost01", "PRIORITY": "6", "SYSLOG_IDENTIFIER": "sshd", "_PID": 1234, "MESSAGE": "Accepted publickey"}'
    event = parser.parse(line, line_number=1)

    assert event.source == 'journald'
    assert event.level == 'INFO'
    assert event.message == 'Accepted publickey'
    assert event.metadata == {
        'host': 'webhost01',
        'priority': 6,
        'identifier': 'sshd',
        'pid': 1234,
    }
    # 1779967382.5 Unix timestamp = 2026-05-28 11:23:02.500000 UTC
    assert event.timestamp == datetime(2026, 5, 28, 11, 23, 2, 500000, tzinfo=timezone.utc)


def test_journald_parser_priorities() -> None:
    '''
    Test journald Priority code level mapping.
    '''
    parser = JournaldJsonParser(source_name='journald')

    # PRIORITY <= 3 -> ERROR
    l1 = '{"__REALTIME_TIMESTAMP": "1779967382500000", "PRIORITY": "3", "MESSAGE": "err"}'
    assert parser.parse(l1).level == 'ERROR'

    # PRIORITY == 4 -> WARNING
    l2 = '{"__REALTIME_TIMESTAMP": "1779967382500000", "PRIORITY": "4", "MESSAGE": "warn"}'
    assert parser.parse(l2).level == 'WARNING'

    # PRIORITY >= 5 -> INFO
    l3 = '{"__REALTIME_TIMESTAMP": "1779967382500000", "PRIORITY": "5", "MESSAGE": "notice"}'
    assert parser.parse(l3).level == 'INFO'


def test_journald_parser_failures() -> None:
    '''
    Test journald parsing failures.
    '''
    parser = JournaldJsonParser(source_name='journald')

    # Malformed JSON
    with pytest.raises(ParseError):
        parser.parse('invalid json string', line_number=1)

    # Missing __REALTIME_TIMESTAMP
    with pytest.raises(ParseError):
        parser.parse('{"MESSAGE": "hello"}', line_number=2)

    # Missing MESSAGE
    with pytest.raises(ParseError):
        parser.parse('{"__REALTIME_TIMESTAMP": "1779967382500000"}', line_number=3)

    # Non-integer timestamp
    with pytest.raises(ParseError):
        parser.parse('{"__REALTIME_TIMESTAMP": "bad-timestamp", "MESSAGE": "hello"}', line_number=4)


# ==============================================================================
# CustomRegexParser Tests
# ==============================================================================

def test_custom_parser_success() -> None:
    '''
    Test custom regex parser with custom pattern, level casing, and extra groups.
    '''
    pattern = r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T[\d:.]+Z)\s+(?P<level>\w+)\s+\[(?P<component>[^\]]+)\]\s+(?P<message>.+)$'
    parser = CustomRegexParser(source_name='app', pattern=pattern, timezone_str='UTC')
    line = '2026-05-27T11:23:15.999Z ERROR [app.db] Connection failed'
    event = parser.parse(line, line_number=1)

    assert event.source == 'app'
    assert event.level == 'ERROR'
    assert event.message == 'Connection failed'
    assert event.metadata == {
        'component': 'app.db',
    }
    assert event.timestamp == datetime(2026, 5, 27, 11, 23, 15, 999000, tzinfo=timezone.utc)


def test_custom_parser_failures() -> None:
    '''
    Test custom regex parser instantiation and parsing failures.
    '''
    # Empty pattern
    with pytest.raises(ValueError):
        CustomRegexParser(source_name='app', pattern='', timezone_str='UTC')

    # Invalid regex
    with pytest.raises(ValueError):
        CustomRegexParser(source_name='app', pattern='[invalid-regex', timezone_str='UTC')

    # Invalid timezone
    with pytest.raises(TimezoneError):
        CustomRegexParser(source_name='app', pattern='(?P<timestamp>.*)', timezone_str='Invalid/Zone')

    # Line pattern mismatch
    parser = CustomRegexParser(source_name='app', pattern=r'^(?P<timestamp>\d+)\s+(?P<message>.*)$', timezone_str='UTC')
    with pytest.raises(ParseError):
        parser.parse('bad-line-content', line_number=1)

    # Missing timestamp capture group in pattern
    parser_no_ts = CustomRegexParser(source_name='app', pattern=r'^(?P<message>.*)$', timezone_str='UTC')
    with pytest.raises(ParseError):
        parser_no_ts.parse('hello world', line_number=2)

    # Invalid timestamp matched
    parser_bad_ts = CustomRegexParser(source_name='app', pattern=r'^(?P<timestamp>\S+)\s+(?P<message>.*)$', timezone_str='UTC')
    with pytest.raises(ParseError):
        parser_bad_ts.parse('bad-timestamp hello', line_number=3)
