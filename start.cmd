@echo off

echo.
echo Restoring backend python packages
echo.
call python -m pip install -r requirements.txt
if "%errorlevel%" neq "0" (
    echo Failed to restore backend python packages
    exit /B %errorlevel%
)

echo.
echo Restoring frontend npm packages
echo.
cd frontend
call npm install
if "%errorlevel%" neq "0" (
    echo Failed to restore frontend npm packages
    exit /B %errorlevel%
)

echo.
echo Building frontend
echo.
call npm run build
if "%errorlevel%" neq "0" (
    echo Failed to build frontend
    exit /B %errorlevel%
)

echo.    
echo Starting backend    
echo.    
cd ..  
@REM start http://127.0.0.1:50505
@REM call gunicorn app:app  

:: NISM
:: Start Uvicorn server in a new command prompt window
start cmd /k uvicorn app:app

:: Delay for a few seconds to allow the server to start up (adjust the timeout as necessary)
timeout /t 5

:: Open the default web browser at the server's address
start http://127.0.0.1:50505


if "%errorlevel%" neq "0" (    
    echo Failed to start backend    
    exit /B %errorlevel%    
) 
