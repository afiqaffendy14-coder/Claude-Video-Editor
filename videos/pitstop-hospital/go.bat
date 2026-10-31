@echo off
rem One command: bake the 35 shots, render them on the GPU, then grade + captions + voiceover + SFX into the final MP4.
rem   go.bat            (EEVEE, fastest)        go.bat cycles   (path traced, slower)
rem Needs Blender 5.x and ffmpeg (winget install BlenderFoundation.Blender  /  winget install Gyan.FFmpeg).
setlocal
cd /d "%~dp0"
set ENGINE=%1
if "%ENGINE%"=="" set ENGINE=eevee
set "BLENDER=blender"
where blender >nul 2>nul
if errorlevel 1 (
  for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
)
echo Using Blender: %BLENDER%
echo [0/3] Checking for broken frames from an earlier run...
"%BLENDER%" -b --factory-startup --python tools\frames_fix.py -- out\frames %REDO% || goto :fail
echo [1/3] Baking the 35 shots...
"%BLENDER%" -b --factory-startup --python blender\bake.py -- out\blend || goto :fail
echo [2/3] Rendering 1800 frames with %ENGINE% (re-run to resume if interrupted)...
"%BLENDER%" -b --python blender\render.py -- out\blend out\frames %ENGINE% || goto :fail
echo [3/3] Grading, captions, voiceover and sound...
"%BLENDER%" -b --factory-startup --python tools\compose.py -- out\frames 30 assets\captions_1080 assets\audio\sfx_full.flac 0 60 out\pitstop-hospital-final.mp4 1080 1920 || goto :fail
echo DONE: %CD%\out\pitstop-hospital-final.mp4
start "" "%CD%\out"
pause
exit /b 0
:fail
echo FAILED - see the messages above.
pause
exit /b 1
