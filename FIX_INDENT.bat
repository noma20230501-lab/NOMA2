@echo off
echo ========================================
echo Python indent fix
echo ========================================
echo.

REM autopep8 install check
python -m pip show autopep8 > nul 2>&1
if errorlevel 1 (
    echo Installing autopep8...
    python -m pip install autopep8
)

echo.
echo Fixing indent errors...
echo.

REM Fix all Python files
for %%f in (*.py) do (
    echo   - %%f
    python -m autopep8 --in-place --aggressive --aggressive "%%f"
)

REM Fix Python files in pages folder
if exist pages (
    for %%f in (pages\*.py) do (
        echo   - %%f
        python -m autopep8 --in-place --aggressive --aggressive "%%f"
    )
)

echo.
echo ========================================
echo Done!
echo ========================================
pause
