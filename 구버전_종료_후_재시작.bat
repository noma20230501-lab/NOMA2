@echo off
echo ========================================
echo 구버전 프로그램 종료 중...
echo ========================================

REM 포트 8502를 사용하는 프로세스 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8502 ^| findstr LISTENING') do (
    echo 프로세스 ID %%a 종료 중...
    taskkill /F /PID %%a 2>nul
)

echo.
echo ========================================
echo 잠시 대기 중...
echo ========================================
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo 최신 버전 시작 중...
echo ========================================
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

REM 최신 버전 실행
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8502

pause
