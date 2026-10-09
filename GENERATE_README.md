# Generate All Figures and Tables

This document explains how to run the generation scripts to produce all figures and tables for the HAPS Ground Communications project.

## Quick Start

Choose your preferred method based on your shell:

### **WSL (Recommended - Auto-activates quantum_env)**
```bash
bash generate_all_wsl.sh
```

### **Python (Windows PowerShell)**
```bash
python generate_all.py
```

### **Bash (Git Bash / Unix)**
```bash
bash generate_all.sh
```

### **PowerShell (Windows)**
```powershell
.\generate_all.ps1
```

## WSL Support

If you're using **WSL (Windows Subsystem for Linux)** with the `quantum_env` virtual environment:

### From WSL Terminal
```bash
# Navigate to project
cd /mnt/c/Github/haps_ground_communications

# Run the WSL-optimized script (auto-activates quantum_env)
bash generate_all_wsl.sh
```

**Key Features:**
- ✅ Automatically activates `quantum_env` for `channel_model.py`
- ✅ Deactivates after each script
- ✅ Other generators run in current environment
- ✅ All outputs copied to Windows-accessible paths

### Virtual Environment Details
- **Location:** `~/miniconda3/envs/quantum_env`
- **Auto-activated for:** `channel_model.py`
- **Other scripts:** Run in current shell environment

## What These Scripts Do

1. **Data Generation** - Runs any Python scripts in `src/data/`
2. **Model Generation** - Runs channel and battery models from `src/models/`
3. **Figure & Table Generation** - Runs all generator scripts from `src/generators/`
4. **LaTeX Compilation** - Compiles network diagram if present
5. **Copy Outputs** - Copies all generated files to:
   - `figures/` - PNG and PDF figures
   - `appendix_tables/` - CSV, TEX, and TXT tables

## Improvements Over Old Scripts

### ✅ Fixed Issues
- **Removed references to non-existent scripts:**
  - ❌ `sinr_plot.py` 
  - ❌ `sinr_plot_with_los.py`
  - ❌ `plot_atmospheric_losses_frequency.py`
  - ❌ `compact_tables.py`
  - ❌ `table_b1_scenarios.py`

- **Only runs scripts that actually exist** - Uses dynamic discovery rather than hardcoded paths

- **Proper output copying** - Automatically copies all generated PNG, PDF, CSV, TEX, and TXT files to the correct directories

- **Better error handling** - Continues even if individual scripts fail, reports summary at the end

- **Cross-platform support** - Works on Windows (PowerShell), Git Bash, and Unix systems

### 📁 Directory Structure

```
haps_ground_communications/
├── generate_all.py          # Python version (recommended)
├── generate_all.sh          # Bash version
├── generate_all.ps1         # PowerShell version
├── figures/                 # Output: PNG and PDF figures
├── appendix_tables/         # Output: CSV, TEX, and TXT tables
└── src/
    ├── generators/          # Input: Figure/table generator scripts
    ├── models/              # Input: Channel and battery models
    ├── data/                # Input: Data generation scripts
    ├── output/              # Intermediate: Raw generator outputs
    ├── plots/               # Input: Source plots (e.g., LaTeX diagrams)
    └── ...
```

## Generator Scripts

The following scripts are automatically discovered and run from `src/generators/`:

- `generate_figure_1b_fspl_comparison.py` - Free space path loss comparison
- `generate_figure_5_multinode.py` - Multi-node figure
- `generate_figure7_multinode.py` - Multi-node figure variant
- `generate_figure_9b_scintillation_comparison.py` - Scintillation comparison
- `generate_sinr_heatmap.py` - SINR heatmap visualization
- `generate_sinr_table.py` - SINR table generation
- `generate_sinr_table_2d_spatial.py` - 2D spatial SINR table
- `generate_pathloss_table.py` - Path loss table
- `generate_atm_loss_tables.py` - Atmospheric loss tables
- `generate_constellation_diagram.py` - Constellation diagram
- `generate_figures.py` - General figures
- `generate_phase2_figures.py` - Phase 2 figures
- `make_seed_figure.py` - Seed figure
- `replot_variants.py` - Plot variants

## Model Scripts

From `src/models/`:

- `channel_model.py` - Channel modeling
- `battery_model.py` - Battery modeling

## Troubleshooting

### CMake Needs nmake (Windows)
On Windows, use Unix Makefiles instead:
```bash
cd build
cmake .. -G "Unix Makefiles"
make generate
```

Or skip CMake entirely and use Python/Bash scripts directly (see Quick Start above).

### Permission Denied (Git Bash/Unix)
```bash
chmod +x generate_all.sh
bash generate_all.sh
```

### Permission Denied in WSL
```bash
chmod +x generate_all_wsl.sh
bash generate_all_wsl.sh
```

### Python Not Found
Ensure Python is in your PATH. Check with:
```
python --version
```

### pdflatex Not Found (Optional)
LaTeX compilation is optional. The script will skip if `pdflatex` is not installed. To install:
- **Windows (Chocolatey):** `choco install miktex`
- **Windows (Manual):** Download from https://miktex.org/
- **Mac:** `brew install basictex`
- **Linux:** `sudo apt install texlive` (Ubuntu/Debian)

### Scripts Still Failing
The script will report which scripts failed and continue. Check the error output above each script name. Individual script issues may require:
1. Installing missing dependencies (matplotlib, numpy, etc.)
2. Checking if required data files exist
3. Reviewing individual script documentation in `src/generators/`

## Output Summary

After running, check:
- `figures/` - Final figures for your document
- `appendix_tables/` - Final tables for appendices
- `src/output/` - Raw generator outputs (for debugging)
- Console output - Summary of what ran and what failed

## Notes

- Scripts run in order and are independent
- If a script fails, others will still run
- Existing files in output directories are not overwritten (uses `-n` flag for copy)
- The Python version is recommended for best cross-platform compatibility
