@echo off
chcp 65001 >nul
echo ==========================================
echo   高一学习助手 - 本地服务器
echo ==========================================
echo.

cd /d "f:\陈建文\AI\高中\junyu"

echo 正在启动本地服务器...
echo.
echo 手机和电脑连同一个WiFi
echo 手机浏览器打开以下地址：
echo.
echo   http://10.10.10.217:8000
echo.
echo 按Ctrl+C停止服务器
echo ==========================================
echo.

"C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe" -m http.server 8000
