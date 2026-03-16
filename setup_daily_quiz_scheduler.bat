@echo off
:: =============================================================================
:: setup_daily_quiz_scheduler.bat
:: Registers a Windows Task Scheduler job that runs `generate_daily_quizzes`
:: every day at 06:00 AM (local time).
::
:: HOW TO USE:
::   1. Right-click this file and choose "Run as administrator".
::   2. The task will be created and will start running tomorrow at 06:00 AM.
::   3. To change the time: edit the /ST value below (HH:MM format).
::   4. To remove the task later:
::         schtasks /Delete /TN "CollegePortal_DailyQuiz" /F
:: =============================================================================

setlocal

:: ── Configuration ─────────────────────────────────────────────────────────────
set TASK_NAME=CollegePortal_DailyQuiz
set PROJECT_DIR=c:\Users\Naveen\OneDrive\Documents\collegeportal_314 - Copy
set PYTHON_EXE=python
set START_TIME=06:00

:: ── Build the command that will be executed ───────────────────────────────────
::   We write a small helper .bat so Task Scheduler can call it without troubles
set RUNNER_BAT=%PROJECT_DIR%\run_daily_quiz.bat

(
echo @echo off
echo cd /d "%PROJECT_DIR%"
echo %PYTHON_EXE% manage.py generate_daily_quizzes ^>^> "%PROJECT_DIR%\logs\daily_quiz.log" 2^>^&1
) > "%RUNNER_BAT%"

:: Create the logs folder if it doesn't exist
if not exist "%PROJECT_DIR%\logs" (
    mkdir "%PROJECT_DIR%\logs"
    echo Created logs directory: %PROJECT_DIR%\logs
)

:: ── Register the task ─────────────────────────────────────────────────────────
echo.
echo Registering Windows Task Scheduler job: %TASK_NAME%
echo   Schedule : Daily at %START_TIME%
echo   Runner   : %RUNNER_BAT%
echo.

schtasks /Create /TN "%TASK_NAME%" ^
         /TR "\"%RUNNER_BAT%\"" ^
         /SC DAILY ^
         /ST %START_TIME% ^
         /RL HIGHEST ^
         /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  SUCCESS! Task "%TASK_NAME%" has been scheduled.
    echo  Daily quizzes will be generated every day at %START_TIME%.
    echo.
    echo  To verify, run:
    echo    schtasks /Query /TN "%TASK_NAME%" /FO LIST /V
) else (
    echo.
    echo  ERROR: Could not create the task. Make sure you ran this as Administrator.
)

pause
endlocal
