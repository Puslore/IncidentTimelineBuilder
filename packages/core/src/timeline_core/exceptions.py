from __future__ import annotations


class ParseError(Exception):
    '''
    Raised when a log line cannot be parsed.

    Attributes:
        line_number (int): Line number where parsing failed.
        source_name (str): Name of the log source being parsed.
    '''

    def __init__(
        self,
        message: str,
        line_number: int = 0,
        source_name: str = '',
    ) -> None:
        '''
        Initialize ParseError.

        Args:
            message (str): Description of the parse failure.
            line_number (int): Line number where parsing failed.
            source_name (str): Name of the log source being parsed.
        '''
        self.line_number = line_number
        self.source_name = source_name
        super().__init__(message)


class InvalidFormatError(ValueError):
    '''
    Raised when an unknown or unsupported log format is specified.

    Attributes:
        format_name (str): The format string that was not recognized.
    '''

    def __init__(
        self,
        message: str,
        format_name: str = '',
    ) -> None:
        '''
        Initialize InvalidFormatError.

        Args:
            message (str): Description of the format error.
            format_name (str): The format string that was not recognized.
        '''
        self.format_name = format_name
        super().__init__(message)


class TimezoneError(ValueError):
    '''
    Raised when timezone information is invalid or missing.

    Attributes:
        timezone_value (str): The invalid timezone string.
    '''

    def __init__(
        self,
        message: str,
        timezone_value: str = '',
    ) -> None:
        '''
        Initialize TimezoneError.

        Args:
            message (str): Description of the timezone error.
            timezone_value (str): The invalid timezone string.
        '''
        self.timezone_value = timezone_value
        super().__init__(message)


class ValidationError(Exception):
    '''
    Raised when configuration validation fails.

    Attributes:
        field_name (str): Name of the field that failed validation.
    '''

    def __init__(
        self,
        message: str,
        field_name: str = '',
    ) -> None:
        '''
        Initialize ValidationError.

        Args:
            message (str): Description of the validation failure.
            field_name (str): Name of the field that failed validation.
        '''
        self.field_name = field_name
        super().__init__(message)
