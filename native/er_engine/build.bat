@echo off
rem Buduje dinput8.dll (proxy) do dist\mods\c0000_er_engine\bin\
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set OUT=%~dp0..\..\dist\mods\c0000_er_engine\bin
rem Optional argument: output directory (isolated test builds, e.g. dist\mods\c0000_er_engine_night\bin)
if not "%~1"=="" set OUT=%~1
if not exist "%OUT%" mkdir "%OUT%"
set MH=C:\Users\nemos\workspace\toolsy\minhook
cl /nologo /O2 /MT /W3 /EHsc /LD /I"%MH%\include" "%~dp0er_engine.cpp" "%MH%\src\buffer.c" "%MH%\src\hook.c" "%MH%\src\trampoline.c" "%MH%\src\hde\hde64.c" /Fo"%OUT%\\" /Fe"%OUT%\dinput8.dll" /link /DEF:"%~dp0dinput8.def" user32.lib || exit /b 1
del "%OUT%\*.obj" "%OUT%\*.exp" "%OUT%\*.lib" 2>nul
rem Ten sam modul jako zwykly DLL dla ModEngine2 (external_dlls) - zalecana droga.
copy /y "%OUT%\dinput8.dll" "%OUT%\er_engine.dll" >nul
echo OK: %OUT%\dinput8.dll
