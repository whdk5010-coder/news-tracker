@echo off
chcp 65001 >nul 2>&1
title 경제 뉴스 트래커
echo.
echo  ■ 경제 뉴스 트래커를 시작합니다...
echo  ■ 브라우저가 자동으로 열립니다.
echo  ■ 이 창을 닫으면 트래커가 종료됩니다.
echo.

cd /d "%~dp0"

:: Python 서버 실행 (서버가 브라우저를 자동으로 엶)
python -X utf8 server.py
pause
