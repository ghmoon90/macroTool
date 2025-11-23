@echo off
call clearprj.cmd

set "apps=macrotool"
pyinstaller --onefile --noconsole %apps%.py --icon=%apps%.ico --version-file=%apps%.meta
copy /y dist\%apps%.exe %apps%.exe
call clearprj.cmd
del *.spec