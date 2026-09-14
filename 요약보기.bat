@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 인사·총무 요약 (교육용 가상 자료)

:menu
cls
echo.
echo  ==========================================================
echo    인사·총무 요약  -  교육용 가상 자료
echo  ==========================================================
echo.
echo    1. 전체 브리핑   (오늘 처리할 것 모두)
echo    2. 휴가 · 근태
echo    3. 비품 · 자산
echo    4. 법인카드 · 경비
echo    5. 급여 · 인건비
echo    0. 끝내기
echo.
set "sel="
set /p sel=  번호를 누르고 엔터 (그냥 엔터 = 1):

if "%sel%"=="" set sel=1
if "%sel%"=="0" exit
if "%sel%"=="1" set topic=전체
if "%sel%"=="2" set topic=휴가
if "%sel%"=="3" set topic=자산
if "%sel%"=="4" set topic=카드
if "%sel%"=="5" set topic=급여
if not defined topic goto menu

echo.
python gemini_summary.py %topic%
set topic=
echo.
echo  ----------------------------------------------------------
pause
goto menu
