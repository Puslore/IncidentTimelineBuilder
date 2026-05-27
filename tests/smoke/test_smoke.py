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

    result = subprocess.run(
        [sys.executable, str(cli_path), str(config_path)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert 'timeline' in data
    assert 'stats' in data

    timeline = data['timeline']
    stats = data['stats']

    assert len(timeline) == 4
    for event in timeline:
        assert event['source'] == 'nginx-access'
        assert event['level'] in ('INFO', 'ERROR')
        assert event['timestamp'].endswith('+00:00')

    timestamps = [e['timestamp'] for e in timeline]
    assert timestamps == sorted(timestamps)

    assert stats['total_events'] == 4
    assert stats['by_source'] == {'nginx-access': 4}
    assert stats['by_level'] == {'INFO': 3, 'ERROR': 1}
    assert stats['time_range']['start'] == '2026-05-27T11:23:05+00:00'
    assert stats['time_range']['end'] == '2026-05-27T11:23:25+00:00'
