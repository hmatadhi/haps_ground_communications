# Setup and Installation Guide

## Prerequisites

- **Python:** 3.8 or higher
- **Git:** For version control
- **WSL (Windows users):** For running channel_model.py with quantum_env

## Installation Steps

### 1. Clone or Navigate to Project

```bash
cd ~/haps_ground_communications
```

### 2. Install Dependencies

#### Option A: Standard Python Environment

```bash
pip install -r requirements.txt
```

#### Option B: WSL with Conda (quantum_env)

```bash
# Activate the virtual environment
conda activate quantum_env

# Install requirements
pip install -r requirements.txt
```

#### Option C: Create New Conda Environment

```bash
# Create new environment
conda create -n haps_env python=3.9 numpy scipy pandas matplotlib

# Activate it
conda activate haps_env

# Or install from requirements
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
python -c "import numpy, matplotlib, pandas, scipy; print('✓ All packages installed')"
```

## Project Structure

```
haps_ground_communications/
├── requirements.txt              # Python dependencies (THIS FILE'S DEPENDENCIES)
├── SETUP.md                      # This file
├── QUICKSTART.md                 # Quick start guide
├── GENERATE_README.md            # Generation script documentation
├── generate_all.py               # Master generation script (Python)
├── generate_all.sh               # Master generation script (Bash)
├── generate_all.ps1              # Master generation script (PowerShell)
├── generate_all_wsl.sh           # Master generation script (WSL-optimized)
│
├── figures/                      # OUTPUT: Final figures for LaTeX
├── appendix_tables/              # OUTPUT: Final tables for LaTeX
│
├── HAPS_AI_HW_ChannelModel.tex   # LaTeX document
├── HAPS_AI_HW_ChannelModel.pdf   # PDF output
│
└── src/                          # Source code directory
    ├── output/                   # Intermediate generated files
    ├── models/
    │   ├── channel_model.py      # Channel propagation model (REQUIRES quantum_env in WSL)
    │   ├── battery_model.py      # Battery model
    │   └── README.md
    ├── generators/               # Figure and table generators
    │   ├── generate_figure_1b_fspl_comparison.py
    │   ├── generate_figure_5_multinode.py
    │   ├── generate_figure7_multinode.py
    │   ├── generate_figure_9b_scintillation_comparison.py
    │   ├── generate_sinr_heatmap.py
    │   ├── generate_sinr_table.py
    │   ├── generate_sinr_table_2d_spatial.py
    │   ├── generate_pathloss_table.py
    │   ├── generate_atm_loss_tables.py
    │   ├── generate_constellation_diagram.py
    │   ├── generate_figures.py
    │   ├── generate_phase2_figures.py
    │   ├── make_seed_figure.py
    │   └── replot_variants.py
    ├── data/                     # Data generation scripts (if any)
    ├── plots/                    # Source plots (LaTeX diagrams)
    └── tables/                   # Table templates
```

## Running the Generation Scripts

### Quick Start (Recommended)

```bash
# WSL users
bash generate_all_wsl.sh

# Standard bash/Git Bash
bash generate_all.sh

# Python (cross-platform)
python generate_all.py

# PowerShell
.\generate_all.ps1
```

### What Gets Generated

1. **Raw outputs** → `src/output/`
2. **Figures** → `figures/`
3. **Tables** → `appendix_tables/`

## Environment Details

### quantum_env (WSL only)

The `channel_model.py` script requires a specific Python environment on WSL:

```bash
# Activate quantum_env
conda activate quantum_env

# Verify packages
python -c "import numpy, scipy, pandas; print('✓ quantum_env ready')"

# Run channel_model directly
python src/models/channel_model.py
```

**Note:** The master scripts automatically detect and activate quantum_env when needed.

## Troubleshooting

### "ModuleNotFoundError: No module named 'numpy'"

```bash
# Install all dependencies
pip install -r requirements.txt

# Or for a specific package
pip install numpy
```

### "channel_model.py failed" (WSL)

```bash
# Check if quantum_env exists
conda info --envs

# Activate it
conda activate quantum_env

# Retry
bash generate_all_wsl.sh
```

### "pdflatex not found"

LaTeX compilation is optional. If you want to compile LaTeX diagrams:

```bash
# Windows (Chocolatey)
choco install miktex

# macOS
brew install basictex

# Linux (Ubuntu/Debian)
sudo apt install texlive-latex-base
```

## Updating Dependencies

To update all packages to latest versions:

```bash
pip install --upgrade -r requirements.txt
```

## Creating a Custom Environment

If you want a clean, isolated environment:

```bash
# Create new environment
python -m venv haps_env

# Activate it
source haps_env/bin/activate    # Linux/macOS
.\haps_env\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. 📖 Read: `QUICKSTART.md` for quick start
3. 🚀 Run: `bash generate_all_wsl.sh` (or your preferred script)
4. 📊 Check: `figures/` and `appendix_tables/` for outputs
