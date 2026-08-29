@echo off
cd /d "%~dp0"

del /f /q HAPS_AI_HW_ChannelModel.aux 2>nul
del /f /q HAPS_AI_HW_ChannelModel.log 2>nul
del /f /q HAPS_AI_HW_ChannelModel.out 2>nul
del /f /q HAPS_AI_HW_ChannelModel.pdf 2>nul

echo.
echo LaTeX generated files cleaned.
