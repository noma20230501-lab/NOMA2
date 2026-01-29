@echo off
chcp 65001 > nul
echo ========================================
echo Python 들여쓰기 자동 수정 프로그램
echo ========================================
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

echo 📝 모든 .py 파일의 들여쓰기를 수정합니다...
echo.

REM autopep8이 설치되어 있는지 확인
python -m pip show autopep8 >nul 2>&1
if errorlevel 1 (
    echo ⚠️ autopep8이 설치되어 있지 않습니다.
    echo 📦 autopep8 설치 중...
    python -m pip install autopep8
    echo.
)

REM 현재 디렉토리의 모든 .py 파일 들여쓰기 수정
echo 🔧 들여쓰기 수정 중...
python -m autopep8 --in-place --aggressive --aggressive *.py

echo.
echo ✅ 들여쓰기 수정 완료!
echo ========================================
pause
