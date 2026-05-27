# Incident Timeline Builder

CLI utility that merges logs from multiple sources into a single
chronological timeline with timestamps normalized to UTC.

## Prerequisites

- Python 3.12+
- Dependencies: `typer`, `rich`, `pyyaml`, `python-dateutil`

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install typer rich pyyaml python-dateutil

# 3. Run the tool
PYTHONPATH=packages/core/src python app/cli/main.py tests/fixtures/sources.valid.yaml
```

## Supported Log Formats

| Format           | Status      |
|------------------|-------------|
| nginx-combined   | ✅ supported |
| syslog           | 🔜 planned  |
| journald-json    | 🔜 planned  |
| custom (regex)   | 🔜 planned  |

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
