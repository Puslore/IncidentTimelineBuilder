# Architecture: Incident Timeline Builder

This document details the software architecture and design principles of the Incident Timeline Builder.

## Layer Separation

The application strictly separates domain/business logic from orchestration/CLI presentation:

```
┌──────────────────────────────────────┐
│             app/cli/                 │
│  (CLI interface, Typer, YAML files)  │
└──────────────────┬───────────────────┘
                   │  Imports & orchestrates
                   ▼
┌──────────────────────────────────────┐
│           packages/core/             │
│   (Domain Models, Parsers, Factory)  │
└──────────────────────────────────────┘
```

1. **`packages/core/`**: Pure domain logic.
   - Has zero knowledge of Typer, stdout/stderr, files, colors, or external arguments.
   - Implements data models as immutable frozen dataclasses (`LogEvent`, `LogSource`, `Timeline`).
   - Standardizes domain exceptions (`ParseError`, `ValidationError`, `TimezoneError`, `InvalidFormatError`).
   - Pure Python standard library implementation only (zero runtime third-party dependencies).
2. **`app/cli/`**: Presentation and orchestration layer.
   - Thin CLI wrapper utilizing Typer, Rich, and PyYAML.
   - Orchestrates loading config, instantiating parsers via registry, reading files, and outputting JSON to stdout.

## Design Patterns

- **Registry & Factory Pattern**: Log parsers inherit from `BaseParser` and are registered in a central registry. The `get_parser(format_name, source_name, ...)` factory instantiates the correct parser class at runtime.
- **Microseconds Precision**: Journald events use microsecond Unix timestamp formats, which are parsed with Python's float precision and converted to UTC timezone-aware `datetime` objects.
- **Dynamic Regex Parsing**: The `CustomRegexParser` compiles regex pattern configurations from YAML, extracting custom fields (like client or component) directly into the event metadata.
