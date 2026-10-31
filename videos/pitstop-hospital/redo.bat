@echo off
rem Re-render just some shots, keeping every other frame. Double-click and type the shot numbers (e.g. 9),
rem or run:  redo.bat 9      redo.bat 9 13
setlocal
cd /d "%~dp0"
set "REDO=%*"
if "%REDO%"=="" set /p "REDO=Which shot numbers to re-render (e.g. 9)? "
call go.bat
