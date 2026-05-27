from __future__ import annotations

from timeline_core.exceptions import InvalidFormatError
from timeline_core.parsers.base import BaseParser
from timeline_core.parsers.nginx_combined import NginxCombinedParser
from timeline_core.parsers.syslog import SyslogParser
from timeline_core.parsers.journald import JournaldJsonParser
from timeline_core.parsers.custom import CustomRegexParser

_REGISTRY: dict[str, type[BaseParser]] = {
    'nginx-combined': NginxCombinedParser,
    'syslog': SyslogParser,
    'journald-json': JournaldJsonParser,
    'custom': CustomRegexParser,
}


def get_parser(format_name: str, source_name: str, timezone_str: str = 'UTC', pattern: str = '') -> BaseParser:
    '''
    Factory function to get a parser instance by format name.

    Args:
        format_name (str): Log format identifier.
        source_name (str): Source label for generated events.
        timezone_str (str): IANA timezone string.
        pattern (str): Optional custom regex pattern.

    Returns:
        BaseParser: Instantiated parser.

    Raises:
        InvalidFormatError: If the format_name is not supported.
    '''
    parser_cls = _REGISTRY.get(format_name)
    if parser_cls is None:
        raise InvalidFormatError(f'Unknown log format: {format_name}', format_name=format_name)

    if format_name == 'nginx-combined':
        return NginxCombinedParser(source_name=source_name)
    elif format_name == 'syslog':
        return SyslogParser(source_name=source_name, timezone_str=timezone_str)
    elif format_name == 'journald-json':
        return JournaldJsonParser(source_name=source_name)
    elif format_name == 'custom':
        return CustomRegexParser(source_name=source_name, pattern=pattern, timezone_str=timezone_str)
    else:
        raise InvalidFormatError(f'Unknown log format: {format_name}', format_name=format_name)


__all__ = [
    'BaseParser',
    'CustomRegexParser',
    'JournaldJsonParser',
    'NginxCombinedParser',
    'SyslogParser',
    'get_parser',
]
