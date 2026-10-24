"""Installation and dependency-boundary checks."""

from pathlib import Path
import subprocess
import sys
import shutil
import venv

import pytest
from graph_ics.colors import hex2rgb #type:ignore


@pytest.mark.parametrize('value, expected', [('#00FFFF', (0, 255, 255)), ('a6b7c8', (166, 183, 200)), ('000000', (0, 0, 0))])
def test_color_parser(value: str, expected: tuple[int, int, int]) -> None:
    assert hex2rgb(value) == expected


@pytest.mark.parametrize('value', ['#abc', '#GG0000', '', '1234567'])
def test_invalid_color(value: str) -> None:
    with pytest.raises(ValueError): hex2rgb(value)


def test_installed_import_outside_checkout(tmp_path: Path) -> None:
    code = "import graph_ics, sys; assert graph_ics.Graph; assert 'cairo' not in sys.modules; assert 'colormap' not in sys.modules; print(graph_ics.__file__)"
    result = subprocess.run([sys.executable, '-I', '-c', code], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert 'src' in result.stdout or 'site-packages' in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows environment helper")
def test_toggle_environment_roundtrip(tmp_path: Path) -> None:
    project = tmp_path / "project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)

    script = scripts / "toggle_venv.ps1"
    shutil.copyfile(Path(__file__).resolve().parents[1] / "scripts" / script.name, script)

    expected_venv = project / ".venv"
    venv.EnvBuilder(with_pip=False).create(expected_venv)

    command = (
        "$ErrorActionPreference = 'Stop'; "
        "Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue; "
        f". '{script}'; "
        f"if ($env:VIRTUAL_ENV -ne '{expected_venv}') {{ throw 'Incorrect environment' }}; "
        f". '{script}'; "
        "if ($env:VIRTUAL_ENV) { throw 'Still active' }"
    )

    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], cwd=tmp_path, check=True, capture_output=True, text=True)

@pytest.mark.skipif(sys.platform != 'win32', reason='Windows environment helper')
def test_toggle_path_with_spaces_and_missing_environment(tmp_path: Path) -> None:
    project = tmp_path / 'project with spaces'
    scripts = project / 'scripts'
    scripts.mkdir(parents=True)
    script = scripts / 'toggle_venv.ps1'
    shutil.copyfile(Path(__file__).resolve().parents[1] / 'scripts' / script.name, script)
    prefix = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command']
    missing = subprocess.run(prefix + [f"$ErrorActionPreference='Stop'; . '{script}'"], cwd=tmp_path, capture_output=True, text=True)
    assert missing.returncode != 0 and 'setup_venv.bat' in missing.stderr
    venv.EnvBuilder(with_pip=False).create(project / '.venv')
    command = f"$ErrorActionPreference='Stop'; . '{script}'; if ($env:VIRTUAL_ENV -ne '{project / '.venv'}') {{ throw 'Wrong path' }}; . '{script}'"
    subprocess.run(prefix + [command], cwd=tmp_path, check=True, capture_output=True)
