@echo off
echo ========================================
echo     Остановка всех копий бота...
echo ========================================
echo.
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM python3.exe /T 2>nul
echo.
echo Готово! Все копии бота остановлены.
echo Теперь можешь запустить start.bat
echo.
pause
