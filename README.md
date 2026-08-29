# HAPS Ground Communications

This repository contains the LaTeX source for the HAPS ground communications paper and related generated artifacts.

## Project structure

- `HAPS_AI_HW_ChannelModel.tex` — main paper source
- `build-paper.bat` — Windows batch script for the LaTeX build
- `CMakeLists.txt` — CMake support for future Python-based generation of figures and tables
- `figures/` — figure assets
- `appendix_tables/` — appendix table sources

## Build the paper

From PowerShell or Command Prompt:

```powershell
cd C:\Github\haps_ground_communications
.\build-paper.bat
```

This runs:

```bat
pdflatex -interaction=nonstopmode HAPS_AI_HW_ChannelModel.tex
pdflatex -interaction=nonstopmode HAPS_AI_HW_ChannelModel.tex
```

## Generate figures and tables

CMake is intended for Python-generated artifacts, not the LaTeX paper compile itself.

```powershell
cmake -S . -B build
cmake --build build --target generate
```

## Clean generated files

Remove LaTeX build artifacts manually:

```powershell
Remove-Item .\HAPS_AI_HW_ChannelModel.aux, .\HAPS_AI_HW_ChannelModel.log, .\HAPS_AI_HW_ChannelModel.out, .\HAPS_AI_HW_ChannelModel.pdf -ErrorAction SilentlyContinue
```

```powershell
cmake --build build --target clean-paper
```

## Notes

- The LaTeX paper build is intentionally kept simple and reliable on Windows.
- Keep generated assets under `figures/` and table sources under `appendix_tables/` for clean project organization.