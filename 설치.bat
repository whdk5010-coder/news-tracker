@echo off
chcp 65001 >nul 2>&1
title 뉴스 트래커 - 패키지 설치
echo.
echo  ■ 필요한 패키지를 설치합니다...
echo.

pip install -r "%~dp0requirements.txt"

echo.
echo  ■ 설치 완료! 이제 "뉴스트래커.bat"을 실행하세요.
echo.
pause
