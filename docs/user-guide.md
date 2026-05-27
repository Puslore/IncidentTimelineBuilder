# User Guide: Incident Timeline Builder

This guide provides instructions for installation, configuration, and execution of the Incident Timeline Builder tool.

## Installation

1. **Prerequisites**: Ensure Python 3.12+ is installed on your system.
2. **Setup virtualenv**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\Activate.ps1 on Windows
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start: `parse` Command

The fastest way to use the tool — pass log file paths directly:

```bash
# Auto-detects format from file name:
python app/cli/main.py parse /var/log/nginx/access.log

# Explicit format and timezone:
python app/cli/main.py parse /var/log/syslog --format syslog --timezone Europe/Moscow

# Multiple files merged into one timeline:
python app/cli/main.py parse access.log syslog.log journald.json

# Save output to a file:
python app/cli/main.py parse access.log > timeline.json
```

### Options

| Option | Short | Description |
|---|---|---|
| `--format` | `-f` | Log format: `nginx-combined`, `syslog`, `journald-json`, `custom`. Auto-detected if omitted. |
| `--timezone` | `-tz` | IANA timezone for timestamps (default: `UTC`). |
| `--pattern` | `-p` | Regex pattern (required when format is `custom`). |
| `--name` | `-n` | Source label for events (default: file name). |

### Format Auto-Detection

When `--format` is not specified, the tool guesses the format from the file name:

| File name contains | Detected format |
|---|---|
| `nginx` | `nginx-combined` |
| `syslog` | `syslog` |
| `journal` | `journald-json` |
| `.json` extension | `journald-json` |

If the format cannot be detected, the tool will ask you to specify `--format` explicitly.

## Advanced: `build` Command (YAML Config)

For complex multi-source setups with mixed formats, timezones, and custom regex patterns, use a YAML configuration file:

```bash
python app/cli/main.py build sources.yaml
```

### Configuration Schema

```yaml
sources:
  - name: nginx-access
    file: tests/fixtures/nginx-access.log
    format: nginx-combined
    timezone: Europe/Moscow

  - name: app
    file: tests/fixtures/app.log
    format: custom
    pattern: '^(?P<timestamp>\d{4}-\d{2}-\d{2}T[\d:.]+Z)\s+(?P<level>\w+)\s+\[(?P<component>[^\]]+)\]\s+(?P<message>.+)$'
    timezone: UTC
```

### Fields

- `sources`: List of log source dictionaries.
  - `name`: Identifier for the log source.
  - `file`: Path to the log file.
  - `format`: Must be one of `nginx-combined`, `syslog`, `journald-json`, `custom`.
  - `timezone`: IANA timezone indicator (e.g. `Europe/Moscow`, `UTC`).
  - `pattern`: Regex pattern (only required when `format` is `custom`). Must capture `(?P<timestamp>...)`.

## Docker Usage

Mount your log files into the container and use the `parse` command:

```bash
# Using docker run:
docker run --rm -v /var/log:/logs timeline-builder parse /logs/nginx/access.log

# Using docker compose:
docker compose -f infra/compose.yaml up --build
```

The output JSON will be printed to stdout.
