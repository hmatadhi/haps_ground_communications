# Quick Start: Generate Figures and Tables

## 🚀 One-Liner Commands

### WSL (Recommended - auto-activates quantum_env)
```bash
cd src && bash generate_all_wsl.sh
```

### Python (Windows PowerShell / Cross-platform)
```powershell
cd src
python generate_all.py
```

### Bash / Git Bash (Windows)
```bash
cd src && bash generate_all.sh
```

### PowerShell (Windows)
```powershell
cd src
.\generate_all.ps1
```

### CMake (with Unix Makefiles)
```bash
cd build
cmake .. -G "Unix Makefiles"
make generate
```

---

## 📋 What Gets Generated

### Input Directories
- `src/generators/` - Python scripts that generate figures/tables
- `src/models/` - Channel and battery model scripts
- `src/data/` - Data generation scripts

### Output Directories
- **`figures/`** ← PNG and PDF figures go here
- **`appendix_tables/`** ← CSV, TEX, and TXT tables go here
- `src/output/` ← Raw generator outputs (for debugging)

---

## 🛠️ What's Fixed

| Issue | Old Scripts | New Scripts |
|-------|------------|-------------|
| **Non-existent script references** | ❌ Hard-coded broken paths | ✅ Dynamic discovery |
| **Error handling** | ❌ Stops on first error | ✅ Continues, reports summary |
| **Cross-platform** | ❌ Bash only | ✅ Python/Bash/PowerShell/CMake |
| **Output copying** | ❌ Manual or incomplete | ✅ Automatic to figures/ & appendix_tables/ |

---

## 📁 New Files Created

```
haps_ground_communications/
├── generate_all.py            # ← Main script (Python - recommended)
├── generate_all.sh            # ← Bash version
├── generate_all.ps1           # ← PowerShell version
├── GENERATE_README.md         # ← Detailed documentation
├── QUICKSTART.md              # ← This file
├── CMakeLists.txt             # ← Updated with new targets
│
├── figures/                   # ← Generated output
├── appendix_tables/           # ← Generated output
└── src/
    ├── generators/            # ← Figure/table generators
    ├── models/                # ← Model generators
    ├── data/                  # ← Data generators
    └── output/                # ← Intermediate outputs
```

---

## ⚡ Quick Troubleshooting

### "Python not found"
Install Python from https://www.python.org or use:
```powershell
winget install Python.Python.3.11
```

### "pdflatex not found" (optional - just skips LaTeX diagrams)
```powershell
# Windows
winget install MiKTeX.MiKTeX

# macOS
brew install basictex

# Linux
sudo apt install texlive-latex-base
```

### "make not found"
Install GNU Make:
```powershell
winget install GnuWin32.Make
```

### Scripts still failing?
- Check the console output - it will show which scripts failed
- The script continues even if individual generators fail
- Review `GENERATE_README.md` for detailed troubleshooting

---

## 📊 Running Individual Stages

You can also run individual stages if needed:

```python
# Python version - modify generate_all.py to comment out stages

# Or run them manually:
python src/data/*.py                          # Data generation
python src/models/channel_model.py            # Models
python src/generators/generate_figures.py    # Figures
```

---

## ✅ Verification

After running, verify outputs:
```powershell
# Check figures were generated
ls figures/ | Measure-Object

# Check tables were generated
ls appendix_tables/ | Measure-Object

# Check raw outputs
ls src/output/ | Measure-Object
```

Should all show files were copied.

---

## 📖 More Information

See **`GENERATE_README.md`** for:
- Detailed explanation of each script
- Complete list of generators
- Directory structure
- Advanced usage
- Full troubleshooting guide
