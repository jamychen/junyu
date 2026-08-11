@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 优先使用系统 PATH 中的 python，回退到已知的 Store 版 Python
where python >nul 2>nul && (
    python main.py
    goto :end
)

set PYSTORE=C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe
if exist "%PYSTORE%" (
    "%PYSTORE%" main.py
    goto :end
)

echo 未找到 Python，请先安装 Python 3（https://www.python.org/）并安装 wxPython：
echo     pip install wxPython
pause

:end
