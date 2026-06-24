@echo off
echo ============================================
echo  MangoDefend - TEST MODE (Realtime Alert)
echo  Semua file .exe akan dianggap MALWARE
echo  Jalankan Notepad atau app lain untuk test
echo ============================================
echo.

set MANGODEFEND_TEST_MALWARE=1
python main.py

echo.
echo [TEST MODE SELESAI]
pause
