@echo off
setlocal
set "PYYAML_FORCE_LIBYAML=0"
if not defined GRAPH_ICS_PYTHON set "GRAPH_ICS_PYTHON=python"
set "PROJECT_ROOT=%~dp0.."
set "GROUP=%~1"
if "%GROUP%"=="" set "GROUP=dev"
if /I "%GROUP%"=="dev" (set "REQUIREMENTS=requirements_dev.txt") else if /I "%GROUP%"=="base" (set "REQUIREMENTS=requirements.txt") else if /I "%GROUP%"=="render" (set "REQUIREMENTS=requirements_render.txt") else (
    echo Unknown group "%GROUP%". Use dev, base, or render.
    exit /b 2
)
pushd "%PROJECT_ROOT%" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
    echo Creating .venv...
    "%GRAPH_ICS_PYTHON%" -m venv .venv
    if errorlevel 1 goto :failed
) else (
    echo Reusing .venv...
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"
if errorlevel 1 goto :failed
echo Environment setup complete.
echo PowerShell: . "%CD%\scripts\toggle_venv.ps1"
echo CMD: call "%CD%\.venv\Scripts\activate.bat"
popd
exit /b 0
:failed
echo Environment setup failed. See the command output above.
popd
exit /b 1
