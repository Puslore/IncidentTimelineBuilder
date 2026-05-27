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
Once the package is installed, run the CLI utility directly:
```bash
python app/cli/main.py tests/fixtures/sources.valid.yaml
```
*(Alternatively, you can run `PYTHONPATH=packages/core/src python app/cli/main.py tests/fixtures/sources.valid.yaml` without installing the package).*

### 4. Run with Docker Compose
To run the timeline builder inside a Docker container:
```bash
make compose-up
```

## Supported Log Formats

| Format           | Status      |
|------------------|-------------|
| nginx-combined   | ✅ supported |
| syslog           | ✅ supported |
| journald-json    | ✅ supported |
| custom (regex)   | ✅ supported |

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
