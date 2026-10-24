"""Selection, failure reporting and documentation preservation for example execution."""
from pathlib import Path
import json
import subprocess
import pytest
from scripts import generate_examples


def test_runner_keeps_readmes_and_runs_only_selected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ('first', 'second'):
        folder = tmp_path/'examples'/name
        folder.mkdir(parents=True)
        (folder/'example.py').write_text('', encoding='utf-8')
        (folder/'README.md').write_text('Handwritten instructions', encoding='utf-8')
    monkeypatch.setattr(generate_examples, 'ROOT', tmp_path)
    monkeypatch.setattr(generate_examples, 'discover', lambda: ('first', 'second'))
    calls: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, 'done', '')

    monkeypatch.setattr(generate_examples.subprocess, 'run', run)
    assert generate_examples.main(['first', '--seed', '19', '--nodes', '80']) == 0
    assert len(calls) == 1 and calls[0][-4:] == ['--seed', '19', '--nodes', '80']
    assert calls[0][2] == 'examples.first.example'
    assert (tmp_path/'examples/first/README.md').read_text(encoding='utf-8') == 'Handwritten instructions'
    report = json.loads((tmp_path/'examples/results.json').read_text(encoding='utf-8'))
    assert report[0]['succeeded'] is True


def test_runner_continues_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path/'examples').mkdir()
    monkeypatch.setattr(generate_examples, 'ROOT', tmp_path)
    monkeypatch.setattr(generate_examples, 'discover', lambda: ('first', 'second'))
    calls: list[str] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command[2])
        return subprocess.CompletedProcess(command, 1 if len(calls) == 1 else 0, '', 'failed' if len(calls) == 1 else '')

    monkeypatch.setattr(generate_examples.subprocess, 'run', run)
    assert generate_examples.main(['--all']) == 1
    assert calls == ['examples.first.example', 'examples.second.example']
