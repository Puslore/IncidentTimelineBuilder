from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_smoke_success() -> None:
    '''
    Smoke test checking the main entrypoint output with valid sources config.
    '''
    project_root = Path(__file__).parent.parent.parent

    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / 'packages' / 'core' / 'src')

    cli_path = project_root / 'app' / 'cli' / 'main.py'
    config_path = project_root / 'tests' / 'fixtures' / 'sources.valid.yaml'
    expected_path = project_root / 'tests' / 'fixtures' / 'expected' / 'timeline.json'

    result = subprocess.run(
        [sys.executable, str(cli_path), 'build', str(config_path)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert result.returncode == 0

    # Parse stdout and expected JSON
    actual_data = json.loads(result.stdout)
    with open(expected_path, encoding='utf-8') as fh:
        expected_data = json.load(fh)

    # Assert they are equal
    assert actual_data == expected_data
