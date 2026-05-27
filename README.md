# Incident Timeline Builder

CLI utility that merges logs from multiple sources into a single
chronological timeline with timestamps normalized to UTC.

## Prerequisites

- Python 3.12+
- Make (optional, for automation targets)

## Quick Start

### 1. Setup Environment
Create a virtual environment and install development dependencies:
```bash
make setup
source .venv/bin/activate  # On Linux/macOS
# or: .venv\Scripts\activate on Windows
```

### 2. Build & Install Core Package
Build the core library package and install it locally:
```bash
make build-lib
make install-lib-local
```

### 3. Run the CLI Tool

**Quick parse** — pass log files directly, no config needed:
```bash
# Auto-detects format from file name:
python app/cli/main.py parse /var/log/nginx/access.log

# Explicit format + timezone:
python app/cli/main.py parse /var/log/syslog --format syslog --timezone Europe/Moscow

# Multiple files at once:
python app/cli/main.py parse nginx.log syslog.log journald.json

# Save result to file:
python app/cli/main.py parse access.log > timeline.json
```

**Advanced: YAML config** — for complex multi-source setups:
```bash
python app/cli/main.py build sources.yaml
```

*(Run without installing the package: prefix with `PYTHONPATH=packages/core/src`)*

### 4. Run with Docker
```bash
# Parse files directly:
docker compose -f infra/compose.yaml up --build

# Or with docker run — mount your logs and parse:
docker run --rm -v /var/log:/logs timeline-builder parse /logs/nginx/access.log --format nginx-combined
```

## Supported Log Formats

| Format           | `--format` value | Auto-detected by filename | Status      |
|------------------|------------------|--------------------------|-------------|
| nginx-combined   | `nginx-combined` | `*nginx*`                | ✅ supported |
| syslog           | `syslog`         | `*syslog*`               | ✅ supported |
| journald-json    | `journald-json`  | `*journal*`, `*.json`    | ✅ supported |
| custom (regex)   | `custom`         | —                        | ✅ supported |

## Project Structure

```
├── app/cli/          # Thin CLI orchestration layer
├── packages/core/    # Pure domain logic (models, parsers, exceptions)
├── tests/
│   ├── fixtures/     # Sample log files and expected outputs
│   └── smoke/        # Smoke tests
├── docs/             # Documentation
├── infra/            # Docker / Compose
└── scripts/          # Helper scripts
```

## Exit Codes

| Code | Meaning               |
|------|-----------------------|
| 0    | Success               |
| 1    | No data / bad data    |
| 2    | Validation error      |
