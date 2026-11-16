@echo off
chcp 65001 >nul
title RealBasicVSR GPU판 torch 교체
echo ============================================
echo  torch CPU판을 GPU판으로 교체합니다 (약 3GB)
echo  이 창을 닫지 말고 기다려 주세요.
echo ============================================
echo.
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
echo       Miniconda: %MINI%

echo torch GPU판 설치 중...
call "%MINI%\Scripts\activate.bat" rbvsr
python -m pip uninstall -y torch torchvision
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu130
if errorlevel 1 python -m pip install torch --index-url https://download.pytorch.org/whl/cu134

cd /d "%USERPROFILE%\rbvsr"
echo.
echo 자가진단 중...
python rbvsr_standalone.py --selftest
python -c "import torch,sys;sys.exit(0 if torch.cuda.is_available() else 1)"
if errorlevel 1 (
  echo.
  echo [실패] GPU가 아직 인식되지 않습니다. 이 화면을 캡처해서 보내 주세요.
) else (
  echo.
  echo [완료] cuda: True 확인됐으면 성공입니다.
)
pause
