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

## Configuration Schema

Log sources are configured via a YAML file. Example:

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
  - `pattern`: Compiled regex pattern (only required when `format` is `custom`). Must capture `(?P<timestamp>...)`.

## Execution

To build the incident timeline, run the CLI utility passing the path to the configuration YAML file:

```bash
# On Linux/macOS:
PYTHONPATH=packages/core/src python app/cli/main.py tests/fixtures/sources.valid.yaml

# Or using the PowerShell script (Windows):
.\scripts\test.ps1
```

The output JSON will be printed to stdout.
