echo off

REM Author - atctam
REM Version 1.0 - tested on Windows 10 Pro 10.0.16299

REM Check no. of arguments
if %3.==. (
	echo Not enough input arguments. 
	echo Usage: %0 "filename" "drop rate" "error rate"
	goto :END
)
if not %4.==. (
	echo Too many input arguments.
	echo Usage: %0 "filename" "drop rate" "error rate"
	goto :END
)

REM Star the simulation
echo Start the server
start cmd /k python test-server2.py localhost %2 %3

REM pause for 1 second
timeout /t 1 /nobreak >nul

echo Start the client
start cmd /k python test-client2.py localhost %1 %2 %3

:END