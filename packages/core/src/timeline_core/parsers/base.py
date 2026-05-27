from __future__ import annotations

import abc

from timeline_core.models import LogEvent


class BaseParser(abc.ABC):
    '''
    Abstract base class for all log format parsers.

    Subclasses must implement the `parse` method to convert
    a raw log line into a normalized LogEvent.
    '''

    @abc.abstractmethod
    def parse(self, line: str, line_number: int = 0) -> LogEvent:
        '''
        Parse a single log line into a LogEvent.

        Args:
            line (str): Raw log line to parse.
            line_number (int): Position of the line in the source file.

        Returns:
            LogEvent: Normalized log event.

        Raises:
            ParseError: If the line cannot be parsed.
        '''
