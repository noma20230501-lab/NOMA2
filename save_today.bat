@echo off
chcp 65001 > nul
echo ========================================
echo 오늘 작업 저장 중...
echo ========================================

REM 현재 날짜 가져오기 (YYYY-MM-DD 형식)
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do (
    set TODAY=%%a-%%b-%%c
)

REM 현재 시간 가져오기 (HH:MM 형식)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
    set NOW=%%a:%%b
)

echo.
echo 📁 변경된 파일 확인...
git status

echo.
echo 💾 저장 중...
git add .

echo.
echo 📝 커밋 메시지: [%TODAY% %NOW%] 일일 작업 저장
git commit -m "[%TODAY% %NOW%] 일일 작업 저장"

echo.
echo 🚀 원격 저장소에 업로드...
git push

echo.
echo ========================================
echo ✅ 저장 완료!
echo ========================================
pause
