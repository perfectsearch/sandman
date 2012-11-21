@echo off

if "%1"=="" goto help
if "%1"=="?" goto help
if "%1"=="-?" goto help
if "%1"=="/?" goto help
if "%1"=="-h" goto help
if "%1"=="--help" goto help

if "%1"=="cr" goto cr
if "%1"=="coderoot" goto cr

if "%1"=="tr" goto tr
if "%1"=="testroot" goto tr

if "%1"=="br" goto br
if "%1"=="builtroot" goto br

if "%1"=="rr" goto rr
if "%1"=="runroot" goto rr

if "%1"=="root" goto root

if "%1"=="bzr" goto whoops

goto handledbypython

:rr
set rest=run
goto changedir

:br
set rest=built
goto changedir

:br2
if exist built.win_x64 cd built.win_x64 && goto end
if exist built.win_32 cd built.win_32 && goto end
echo Can't figure out which targeted platform variant to use.
goto end

:cr
set rest=code
goto changedir

:tr
set rest=test
goto changedir

:root
set rest=
goto changedir

:changedir
if "%2"=="" goto empty
python "%~dp0sadm.py" path %* > "%temp%\~sandbox-path.txt"
goto makeitso

:empty
python "%~dp0sadm.py" path . > "%temp%\~sandbox-path.txt"

:makeitso
set /p SANDBOX_PATH=<"%temp%\~sandbox-path.txt"
if "%SANDBOX_PATH%"=="" goto nosbfound
set SANDBOX_DRIVE=%SANDBOX_PATH:~0,2%
%SANDBOX_DRIVE%
cd "%SANDBOX_PATH%"
if "%rest%"=="built" goto br2
cd "%rest%"
goto end

:nosbfound
echo "%2" does not match exactly one sandbox.
goto end

:whoops
echo This looks like a "bzr" command.

:handledbypython
python "%~dp0sbverb.py" %*
goto end

:help
echo sb <verb> [args]
echo.
echo    cr [sandbox spec]
echo    coderoot [sandbox spec]
echo        Change current working dir to code root of the specified sandbox.
echo.
echo    tr [sandbox spec]
echo    testroot [sandbox spec]
echo        Change current working dir to test root of the specified sandbox.
echo.
echo    root [sandbox spec]
echo        Change current working dir to root of the specified sandbox.
echo.
echo    build [sandbox spec] [options] [targets]
echo        Build the specified sandbox. Use sb build --help for options.
echo.
echo    test [sandbox spec] [options] [categories]
echo        Test the specified sandbox. If the sandbox build is out of date,
echo        is automatically built first unless you pass the --no-auto-build
echo        switch. Use sb test --help for options.
echo.
echo    eval [sandbox spec] [options]
echo        Update, build, and test the specified sandbox. Use sb eval --help
echo        for options.
echo.
echo    verify [sandbox spec] [options]
echo        Build and test the specified sandbox. Options are the same as the
echo        options for eval, except that --no-update is added automatically.
echo.
echo    tpv [sandbox spec]
echo        Display the name of the targeted platform variant for the specified
echo        sandbox.
echo.
echo    properties [sandbox spec]
echo        Display all known properties of the specified sandbox.
echo.
echo    <property name> [sandbox spec]
echo        Display the specific property of the specified sandbox.
echo.

:end
