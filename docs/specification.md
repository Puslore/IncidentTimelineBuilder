# Specification: Incident Timeline Builder

This document outlines the requirements and data format specifications for the Incident Timeline Builder tool.

## Purpose

The utility is designed to merge logs from multiple heterogeneous sources into a single, unified, chronologically sorted timeline. All event timestamps are normalized to the Coordinated Universal Time (UTC) timezone.

## Requirements

1. **Multiple Formats Support**: The core engine must support the following log formats:
   - `nginx-combined`: Standard Nginx web server access logs.
   - `syslog`: Linux system daemon logs without year.
   - `journald-json`: Microsecond-precision systemd journal log blocks.
   - `custom`: Regular expression-based format with named capture groups.
2. **UTC Normalization**: All timestamps from source logs must be converted from their local offset to UTC (ISO8601 string format).
3. **Chronological Merge**: Parsed events from all configured files are merged and ordered chronologically.
4. **Structured JSON Output**: The output is printed to stdout in JSON format, containing a `timeline` list of events and a `stats` dictionary summarizing the incident timeline.

## Exit Codes

- `0`: Success. At least one event was parsed and processed successfully.
- `1`: No data or bad data. Config/files not found or no events could be parsed.
- `2`: Validation error. Source YAML configuration file is malformed or invalid.
