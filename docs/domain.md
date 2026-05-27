# Domain Model Glossary: Incident Timeline Builder

This document establishes the consistent vocabulary and model constraints used throughout the codebase and documentation.

## Core Models

### `LogSource`

Represents a source file configured for parsing.

- **Attributes**:
  - `name` (str): Unique human-readable identifier of the log source.
  - `format` (str): Log format identifier (e.g. `nginx-combined`, `syslog`, `journald-json`, `custom`).
  - `timezone` (str): IANA timezone string indicating the local offset of log timestamps.
  - `file_path` (str): Absolute or relative filesystem path to the log file.
  - `filters` (dict): Dictionary for future log filtering criteria.

### `LogEvent`

A single parsed and normalized log record.

- **Attributes**:
  - `timestamp` (datetime): Timezone-aware datetime normalized to UTC (+00:00).
  - `source` (str): Name of the originating `LogSource`.
  - `level` (str): Severity level of the event (e.g. `INFO`, `WARNING`, `ERROR`, `FATAL`).
  - `message` (str): Event message with diagnostic information (raw text headers/metadata stripped).
  - `metadata` (dict): Extracted structured fields (e.g. `client` IP, `pid`, `host`, `component`).
  - `raw_line` (str): Unmodified log line string.

### `Timeline`

An ordered list of `LogEvent` instances.

- **Attributes**:
  - `events` (list[LogEvent]): Sorted list of events.
  - `start_time` (datetime): Timestamp of the earliest event.
  - `end_time` (datetime): Timestamp of the latest event.
  - `sources` (list[str]): List of all contributing sources names.
