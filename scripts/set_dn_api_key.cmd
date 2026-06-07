@echo off
setlocal EnableExtensions

set "DEFAULT_DN_API_KEY=07dc9c34-7bb6-445b-970a-15a770a064a3"

if "%~1"=="" (
    set "DN_API_KEY=%DEFAULT_DN_API_KEY%"
) else (
    set "DN_API_KEY=%~1"
)

if "%DN_API_KEY%"=="" (
    echo DN_API_KEY is empty. Aborting.
    exit /b 1
)

setx DN_API_KEY "%DN_API_KEY%"
if errorlevel 1 (
    echo Failed to set DN_API_KEY.
    exit /b 1
)

echo DN_API_KEY has been saved persistently.
echo Open a new terminal window to use the updated environment variable.
