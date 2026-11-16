@echo off
chcp 65001 >nul
title 원본 vs 보정본 비교 GIF 만들기
if "%~1"=="" (
  echo 사용법: 원본 영상과 보정본 영상을 이 비교GIF.bat 아이콘 위로 끌어다 놓으세요.
  echo.
  echo   - 원본 1개만 끌어다 놓아도 같은 폴더에서 이름_영상보정.mp4 를 자동으로 찾습니다.
  echo   - 두 개를 같이 놓으면 이름에 _영상보정 이 들어간 쪽을 보정본으로 알아서 구분합니다.
  echo   - 결과는 원본과 같은 폴더에 원본이름_비교.gif 로 생깁니다. ^(앞 8초, 10fps^)
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
if not exist "%USERPROFILE%\rbvsr" mkdir "%USERPROFILE%\rbvsr"
cd /d "%USERPROFILE%\rbvsr"
set B64=%TEMP%\compare_gif.b64
if exist "%B64%" del "%B64%"
echo IyDruYTqtZAgR0lGIOunjOuTpOq4sCAtIOybkOuzuOqzvCDrs7TsoJXrs7jsnYQg64KY656A7Z6IIOu2meyduCBHSUYg7IOd7ISxCiMg7IKs7JqpOiBweX>>"%B64%"
echo Rob24gY29tcGFyZV9naWYucHkg7JuQ67O4LmF2aSBb67O07KCV67O4Lm1wNF0KIyAgIC0g7YyM7J28IDHqsJzrp4wg7KO866m0IOqwmeydgCDtj7TrjZTs>>"%B64%"
echo l5DshJwg7KedKOydtOumhF/smIHsg4Hrs7TsoJUubXA0KeydhCDsnpDrj5nsnLzroZwg7LC+7J2MCiMgICAtIO2MjOydvCAy6rCcIOyjvOuptCDsnbTrpo>>"%B64%"
echo Tsl5AgX+yYgeyDgeuztOyglSDsnbQg65Ok7Ja06rCEIOyqveydtCDrs7TsoJXrs7gKaW1wb3J0IG9zLCBzeXMsIHNodXRpbCwgc3VicHJvY2VzcwoKU1VG>>"%B64%"
echo RklYID0gJ1/smIHsg4Hrs7TsoJUnCkVYVFMgPSBbJy5tcDQnLCAnLmF2aScsICcubW92JywgJy5ta3YnLCAnLm1wZycsICcubXBlZycsICcubXRzJywgJy>>"%B64%"
echo 53bXYnXQpGT05UID0gb3MuZW52aXJvbi5nZXQoJ0NPTVBBUkVfR0lGX0ZPTlQnLCAnQ1xcOi9XaW5kb3dzL0ZvbnRzL21hbGd1bi50dGYnKQoKZGVmIGZp>>"%B64%"
echo bmRfcGFpcihwYXRoKToKICAgIGQgPSBvcy5wYXRoLmRpcm5hbWUob3MucGF0aC5hYnNwYXRoKHBhdGgpKQogICAgc3RlbSwgZXh0ID0gb3MucGF0aC5zcG>>"%B64%"
echo xpdGV4dChvcy5wYXRoLmJhc2VuYW1lKHBhdGgpKQogICAgaWYgU1VGRklYIGluIHN0ZW06CiAgICAgICAgYmFzZSA9IHN0ZW0ucmVwbGFjZShTVUZGSVgs>>"%B64%"
echo ICcnKQogICAgICAgIGZvciBlIGluIEVYVFM6CiAgICAgICAgICAgIGNhbmQgPSBvcy5wYXRoLmpvaW4oZCwgYmFzZSArIGUpCiAgICAgICAgICAgIGlmIG>>"%B64%"
echo 9zLnBhdGguZXhpc3RzKGNhbmQpOgogICAgICAgICAgICAgICAgcmV0dXJuIGNhbmQsIHBhdGgKICAgICAgICByZXR1cm4gTm9uZSwgcGF0aAogICAgY2Fu>>"%B64%"
echo ZCA9IG9zLnBhdGguam9pbihkLCBzdGVtICsgU1VGRklYICsgJy5tcDQnKQogICAgaWYgb3MucGF0aC5leGlzdHMoY2FuZCk6CiAgICAgICAgcmV0dXJuIH>>"%B64%"
echo BhdGgsIGNhbmQKICAgIHJldHVybiBwYXRoLCBOb25lCgpkZWYgZmluZF9mZm1wZWcoKToKICAgIGV4ZSA9IHNodXRpbC53aGljaCgnZmZtcGVnJykKICAg>>"%B64%"
echo IGlmIGV4ZToKICAgICAgICByZXR1cm4gZXhlCiAgICB0cnk6CiAgICAgICAgaW1wb3J0IGltYWdlaW9fZmZtcGVnCiAgICAgICAgcmV0dXJuIGltYWdlaW>>"%B64%"
echo 9fZmZtcGVnLmdldF9mZm1wZWdfZXhlKCkKICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgcGFzcwogICAgcHJpbnQoJ2ZmbXBlZyDspIDruYQg7KSR>>"%B64%"
echo Li4uICjstZzstIgg7ZWcIOuyiCwg7JW9IDI1TUIg64uk7Jq066Gc65OcKScpCiAgICBzdWJwcm9jZXNzLmNoZWNrX2NhbGwoW3N5cy5leGVjdXRhYmxlLC>>"%B64%"
echo AnLW0nLCAncGlwJywgJ2luc3RhbGwnLCAnaW1hZ2Vpby1mZm1wZWcnXSkKICAgIGltcG9ydCBpbWFnZWlvX2ZmbXBlZwogICAgcmV0dXJuIGltYWdlaW9f>>"%B64%"
echo ZmZtcGVnLmdldF9mZm1wZWdfZXhlKCkKCmRlZiBidWlsZF9maWx0ZXIoZHVyLCB3LCBoLCB3aXRoX2xhYmVscyk6CiAgICBjZWxsID0gZidzY2FsZT17d3>>"%B64%"
echo 06e2h9OmZvcmNlX29yaWdpbmFsX2FzcGVjdF9yYXRpbz1kZWNyZWFzZSxwYWQ9e3d9OntofToob3ctaXcpLzI6KG9oLWloKS8yOmNvbG9yPWJsYWNrLGZw>>"%B64%"
echo cz0xMCcKICAgIGcgPSAoZidbMDp2XXRyaW09ZHVyYXRpb249e2R1cn0sc2V0cHRzPVBUUy1TVEFSVFBUUyx7Y2VsbH1bbF07JwogICAgICAgICBmJ1sxOn>>"%B64%"
echo ZddHJpbT1kdXJhdGlvbj17ZHVyfSxzZXRwdHM9UFRTLVNUQVJUUFRTLHtjZWxsfVtyXTsnCiAgICAgICAgIGYnW2xdW3JdaHN0YWNrPTJbaHNdOycpCiAg>>"%B64%"
echo ICBiYXIgPSBmJ3BhZD1pdzppaCszODowOjM4OmNvbG9yPTB4MTQxNDE0JwogICAgaWYgd2l0aF9sYWJlbHM6CiAgICAgICAgYmFyICs9IChmIixkcmF3dG>>"%B64%"
echo V4dD1mb250ZmlsZT0ne0ZPTlR9Jzp0ZXh0PSfsm5Drs7gnOmZvbnRjb2xvcj13aGl0ZTpmb250c2l6ZT0yNjp4PTE0Onk9NyIKICAgICAgICAgICAgICAg>>"%B64%"
echo IGYiLGRyYXd0ZXh0PWZvbnRmaWxlPSd7Rk9OVH0nOnRleHQ9J+uztOygleuzuCc6Zm9udGNvbG9yPXdoaXRlOmZvbnRzaXplPTI2Ong9e3crMTR9Onk9Ny>>"%B64%"
echo IpCiAgICBnICs9IGYnW2hzXXtiYXJ9W3ZpZF07W3ZpZF1zcGxpdFttXVtuXTsnCiAgICBnICs9ICdbbV1wYWxldHRlZ2VuPW1heF9jb2xvcnM9MTYwOnN0>>"%B64%"
echo YXRzX21vZGU9ZGlmZltwYWxdOycKICAgIGcgKz0gJ1tuXVtwYWxdcGFsZXR0ZXVzZT1kaXRoZXI9YmF5ZXI6YmF5ZXJfc2NhbGU9NDpkaWZmX21vZGU9cm>>"%B64%"
echo VjdGFuZ2xlW291dF0nCiAgICByZXR1cm4gZwoKZGVmIG1ha2VfZ2lmKGZmLCBvcmlnLCBlbmgsIG91dCwgZHVyLCB3LCBoLCB3aXRoX2xhYmVscyk6CiAg>>"%B64%"
echo ICBjbWQgPSBbZmYsICcteScsICctbG9nbGV2ZWwnLCAnZXJyb3InLCAnLWknLCBvcmlnLCAnLWknLCBlbmgsCiAgICAgICAgICAgJy1maWx0ZXJfY29tcG>>"%B64%"
echo xleCcsIGJ1aWxkX2ZpbHRlcihkdXIsIHcsIGgsIHdpdGhfbGFiZWxzKSwKICAgICAgICAgICAnLW1hcCcsICdbb3V0XScsIG91dF0KICAgIHIgPSBzdWJw>>"%B64%"
echo cm9jZXNzLnJ1bihjbWQsIGNhcHR1cmVfb3V0cHV0PVRydWUsIHRleHQ9VHJ1ZSwgZW5jb2Rpbmc9J3V0Zi04JywgZXJyb3JzPSdyZXBsYWNlJykKICAgIH>>"%B64%"
echo JldHVybiByLnJldHVybmNvZGUgPT0gMCBhbmQgb3MucGF0aC5leGlzdHMob3V0KSwgci5zdGRlcnIuc3RyaXAoKQoKZGVmIG1haW4oKToKICAgIGFyZ3Mg>>"%B64%"
echo PSBbYSBmb3IgYSBpbiBzeXMuYXJndlsxOl0gaWYgb3MucGF0aC5pc2ZpbGUoYSldCiAgICBpZiBsZW4oYXJncykgPT0gMToKICAgICAgICBvcmlnLCBlbm>>"%B64%"
echo ggPSBmaW5kX3BhaXIoYXJnc1swXSkKICAgIGVsaWYgbGVuKGFyZ3MpID49IDI6CiAgICAgICAgYSwgYiA9IGFyZ3NbMF0sIGFyZ3NbMV0KICAgICAgICBp>>"%B64%"
echo ZiBTVUZGSVggaW4gb3MucGF0aC5iYXNlbmFtZShiKToKICAgICAgICAgICAgb3JpZywgZW5oID0gYSwgYgogICAgICAgIGVsaWYgU1VGRklYIGluIG9zLn>>"%B64%"
echo BhdGguYmFzZW5hbWUoYSk6CiAgICAgICAgICAgIG9yaWcsIGVuaCA9IGIsIGEKICAgICAgICBlbHNlOgogICAgICAgICAgICBvcmlnLCBlbmggPSBhLCBi>>"%B64%"
echo CiAgICBlbHNlOgogICAgICAgIHByaW50KCfsmIHsg4Eg7YyM7J287J2EIOywvuydhCDsiJgg7JeG7Iq164uI64ukLicpCiAgICAgICAgcmV0dXJuIDEKIC>>"%B64%"
echo AgIGlmIG5vdCBvcmlnIG9yIG5vdCBlbmg6CiAgICAgICAgcHJpbnQoJ1vsmKTrpZhdIOynneydtCDrp57ripQg7JiB7IOB7J2EIOywvuyngCDrqrvtlojs>>"%B64%"
echo irXri4jri6QuJykKICAgICAgICBwcmludCgn7JuQ67O46rO8IOuztOygleuzuCjsnbTrpoRf7JiB7IOB67O07KCVLm1wNCnsnYQg6rCZ7J2AIO2PtOuNlO>>"%B64%"
echo yXkCDrkZDqsbDrgpgsIOuRkCDtjIzsnbzsnYQg6rCZ7J20IOuBjOyWtOuLpCDrhpPsnLzshLjsmpQuJykKICAgICAgICByZXR1cm4gMQogICAgb3V0ID0g>>"%B64%"
echo b3MucGF0aC5qb2luKG9zLnBhdGguZGlybmFtZShvcy5wYXRoLmFic3BhdGgob3JpZykpLAogICAgICAgICAgICAgICAgICAgICAgIG9zLnBhdGguc3BsaX>>"%B64%"
echo RleHQob3MucGF0aC5iYXNlbmFtZShvcmlnKSlbMF0gKyAnX+u5hOq1kC5naWYnKQogICAgcHJpbnQoJ+ybkOuzuCAgOicsIG9yaWcpCiAgICBwcmludCgn>>"%B64%"
echo 67O07KCV67O4OicsIGVuaCkKICAgIHByaW50KCfstpzroKUgIDonLCBvdXQpCiAgICBmZiA9IGZpbmRfZmZtcGVnKCkKICAgIGZvciBsYWJlbHMgaW4gKF>>"%B64%"
echo RydWUsIEZhbHNlKToKICAgICAgICBvaywgZXJyID0gbWFrZV9naWYoZmYsIG9yaWcsIGVuaCwgb3V0LCA4LCA0ODAsIDM2MCwgbGFiZWxzKQogICAgICAg>>"%B64%"
echo IGlmIG9rOgogICAgICAgICAgICBicmVhawogICAgICAgIGlmIGxhYmVsczoKICAgICAgICAgICAgcHJpbnQoJ+udvOuyqCDsl4bsnbQg64uk7IucIOyLnO>>"%B64%"
echo uPhO2VqeuLiOuLpC4uLicpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcHJpbnQoJ1vsmKTrpZhdIEdJRiDsg53shLEg7Iuk7YyoOicsIGVycls6NDAw>>"%B64%"
echo XSkKICAgICAgICAgICAgcmV0dXJuIDEKICAgIHNpemUgPSBvcy5wYXRoLmdldHNpemUob3V0KQogICAgaWYgc2l6ZSA+IDIwICogMTAyNCAqIDEwMjQ6Ci>>"%B64%"
echo AgICAgICAgcHJpbnQoJ0dJRuqwgCAyME1C66W8IOuEmOyWtOyEnCDrjZQg7J6R6rKMIOuLpOyLnCDrp4zrk63ri4jri6QuLi4nKQogICAgICAgIG9rLCBl>>"%B64%"
echo cnIgPSBtYWtlX2dpZihmZiwgb3JpZywgZW5oLCBvdXQsIDYsIDQwMCwgMzAwLCBsYWJlbHMpCiAgICAgICAgaWYgb2s6CiAgICAgICAgICAgIHNpemUgPS>>"%B64%"
echo Bvcy5wYXRoLmdldHNpemUob3V0KQogICAgcHJpbnQoZidb7JmE66OMXSB7b3V0fSAoe3NpemUvMTAyNC8xMDI0Oi4xZn1NQiknKQogICAgcmV0dXJuIDAK>>"%B64%"
echo CmlmIF9fbmFtZV9fID09ICdfX21haW5fXyc6CiAgICBzeXMuZXhpdChtYWluKCkpCg==>>"%B64%"
certutil -decode "%B64%" "%USERPROFILE%\rbvsr\compare_gif.py" >nul
python "%USERPROFILE%\rbvsr\compare_gif.py" %*
echo.
pause
