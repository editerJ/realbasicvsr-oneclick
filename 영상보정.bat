@echo off
chcp 65001 >nul
title RealBasicVSR 영상 복원
if "%~1"=="" (
  echo 사용법: 복원할 영상 파일을 이 run.bat 아이콘 위로 끌어다 놓으세요.
  echo 여러 개를 한꺼번에 끌어다 놓으면 순서대로 전부 처리합니다.
  pause
  exit /b
)
set MINI=
if exist "%USERPROFILE%\rbvsr\conda_path.txt" set /p MINI=<"%USERPROFILE%\rbvsr\conda_path.txt"
if not "%MINI%"=="" if exist "%MINI%\Scripts\activate.bat" goto conda_ok
set MINI=
for %%P in ("%USERPROFILE%\miniconda3" "%LOCALAPPDATA%\miniconda3" "C:\ProgramData\miniconda3" "D:\ProgramData\miniconda3" "D:\miniconda3" "D:\Users\%USERNAME%\miniconda3") do if exist "%%~P\Scripts\activate.bat" set MINI=%%~P
if not "%MINI%"=="" goto save_path
echo Miniconda 설치 경로를 자동으로 찾지 못했습니다.
echo 예시: D:\ProgramData\miniconda3
set /p MINI=Miniconda가 설치된 폴더를 붙여넣고 Enter:
if not exist "%MINI%\Scripts\activate.bat" goto conda_fail
:save_path
if not exist "%USERPROFILE%\rbvsr" mkdir "%USERPROFILE%\rbvsr"
echo %MINI%>"%USERPROFILE%\rbvsr\conda_path.txt"
goto conda_ok
:conda_fail
echo [오류] 입력한 경로에 Miniconda가 없습니다. 경로를 확인하고 다시 실행하세요.
pause
exit /b 1
:conda_ok
call "%MINI%\Scripts\activate.bat" rbvsr
cd /d "%USERPROFILE%\rbvsr"
set OK=0
set FAIL=0

:loop
if "%~1"=="" goto done
echo.
echo ============================================
echo 복원 시작: %~1
echo ============================================
python rbvsr_standalone.py --input "%~1" --video "%~dpn1_영상보정.mp4" --max-seq-len 40
if errorlevel 1 (
  echo [실패] %~nx1 - 이 파일은 건너뛰고 다음으로 넘어갑니다.
  set /a FAIL+=1
) else (
  echo [완료] %~dpn1_영상보정.mp4
  set /a OK+=1
)
shift
goto loop

:done
echo.
echo ============================================
echo 전체 완료: 성공 %OK%개, 실패 %FAIL%개
echo ============================================
pause
