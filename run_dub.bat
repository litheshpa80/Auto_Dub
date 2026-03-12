@echo off
echo Starting dubbing script...
"f:\VC\venv\Scripts\python.exe" "f:\VC\dub_video_clone.py" "F:\YTDown.com_YouTube_Media_PVmjH3U4xCs_002_720p.mp4" "F:\VC\output_perfect_sync.mp4" --duck-level -50 --keep-temp
echo.
echo Done! Exit code: %ERRORLEVEL%
pause
