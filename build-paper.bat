@echo off
cd /d "%~dp0"

pdflatex -interaction=nonstopmode HAPS_AI_HW_ChannelModel.tex
pdflatex -interaction=nonstopmode HAPS_AI_HW_ChannelModel.tex

echo.
echo Paper build complete.
