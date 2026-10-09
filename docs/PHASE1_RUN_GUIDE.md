# Phase 1 run guide: propagation and channel-model characterization

This guide covers the workflow that produces `HAPS_AI_HW_ChannelModel.tex`'s
Sections I-IV: the physics-based propagation model (HAPS free-space path loss, UAV
air-to-ground path loss/SINR, 38 GHz feeder-link atmospheric losses, tropospheric
scintillation per ITU-R P.618, and multi-HAPS interference across the 3-HAPS
constellation) and the closed-form random-vs-max-SINR association baseline
(Section III.D / IV.D). 

It does **not** cover the DQN association agent — that is
Phase 2; see [`docs/PHASE2_RUN_GUIDE.md`](PHASE2_RUN_GUIDE.md).

## 1. What this is, and how it maps to the paper

| Paper section | Content | Primary source |
|---|---|---|
| I. Introduction | Platform overview, atmospheric impacts | — (no figures) |
| II. System Geometry and Link Types | Network topology, feeder link geometry | `src/plots/network_diagram.tex` |
| III.A-C. System and Channel Model | FSPL, feeder-link atmospheric/scintillation model, service-link LoS/path-loss/SINR model | `src/models/channel_model.py` |
| III.D. Multi-HAPS User Association | State/baseline-policy setup for the random-vs-max-SINR experiment | `src/drl_dqn/haps_association_env.py`, `src/drl_dqn/eval_baseline_association.py` (see Phase 2 guide) |
| IV.A-C. Results | FSPL, path-loss/SINR, atmospheric-loss, multi-node interference, and scintillation figures/tables | `src/models/channel_model.py` + `src/generators/`, `src/plots/` |
| IV.D. Association Baseline Results | Random vs. max-SINR table (`tab:assoc-baseline-results`) | `src/drl_dqn/eval_baseline_association.py` (Phase 2 guide, Section 6) |

`src/models/channel_model.py` is the primary engine: it implements the equations
from Arani, Hu & Zhu (2023) directly and, when run, produces most of the Section IV
figures itself (see Section 5 below for the exact mapping). The scripts under
`src/generators/` fill in the remaining figures plus every appendix table; a few
figures referenced by the paper come from standalone scripts under `src/plots/`
that are **not** wired into the master generation script (Section 4 flags these).

## 2. The stack

- `src/models/channel_model.py` — FSPL, UAV LoS/path-loss/SINR, multi-HAPS
  interference, scintillation fade depth/margin/time-series; the equations
  implementing paper Eqs. 1-12
- `src/models/channel_model.py`'s `haps_constellation_geometry()` /
  `haps_a2g_pathloss_db()` — the 65 km equilateral-triangle 3-HAPS geometry reused
  by every downstream generator and by Phase 2
- `src/generators/` — figure and table generators driven off `channel_model.py`'s
  functions or off its CSV outputs (Section 5 has the full list)
- `src/plots/` — atmospheric-loss-vs-frequency and SINR-trellis figure scripts, plus
  `network_diagram.tex` (compiled separately with `pdflatex`)
- `src/tables/`, `src/appendix_tables/`, `src/appendix_data/` — appendix table
  sources, generated `.tex` table fragments, and their archived `.csv` data
- `src/generate_all_wsl.sh` — orchestrates most (not all — see Section 4) of the
  above, in dependency order, from a WSL/Linux shell
- `build-paper.bat` / `clean-paper.bat` — compile/clean the paper PDF via `pdflatex`

## 3. Setup

From the repo root:

```powershell
cd C:\Github\haps_ground_communications
python -m pip install -r src/requirements.txt
```

`channel_model.py` itself only needs NumPy + Matplotlib; the generators also use
SciPy and pandas (all covered by `src/requirements.txt`).

Every script under `src/generators/` and `src/plots/` imports other project modules
as top-level packages (e.g. `from models.channel_model import ...`,
`from plots.atmospheric_losses import ...`), and several read/write paths relative
to `src/output/` (e.g. `output/sinr_multinode_spatial_table.csv`). Both of these
only resolve correctly if **`src/` is on `PYTHONPATH` and is the current working
directory** when you invoke a script — the same convention `generate_all_wsl.sh`
uses internally (`cd src && PYTHONPATH=src python generators/<script>.py`).

PowerShell:

```powershell
cd C:\Github\haps_ground_communications\src
$env:PYTHONPATH = "C:\Github\haps_ground_communications\src"
```

## 4. Run commands

### 4a. WSL / Linux — the master script

```bash
cd /path/to/haps_ground_communications
./src/generate_all_wsl.sh
```

This runs, in order: `channel_model.py` and `battery_model.py` (Stage 2), then the
`src/generators/` scripts in this dependency order (Stage 3):

```text
generate_sinr_table_2d_spatial.py   # MUST run first — writes the CSV the next 3 read
generate_constellation_diagram.py
generate_figure_5_multinode.py
generate_sinr_heatmap.py
generate_figure_1b_fspl_comparison.py
generate_figure7_multinode.py
generate_figure_9b_scintillation_comparison.py
generate_sinr_table.py
generate_pathloss_table.py
generate_atm_loss_tables.py
generate_figures.py
generate_phase2_figures.py
```

It looks for a `quantum_env` conda environment for the `channel_model.py` step;
that is optional convenience, not a hard requirement — any Python environment with
`src/requirements.txt` installed works.

All outputs land in `src/output/`. The script prints a reminder to copy them into
the paper's directories (see Section 6).

### 4b. Windows PowerShell — manual equivalent

`generate_all_wsl.sh` is bash-only. On Windows, run the same steps directly (from
`src/`, with `PYTHONPATH` set per Section 3):

```powershell
python models\channel_model.py
python models\battery_model.py

python generators\generate_sinr_table_2d_spatial.py
python generators\generate_constellation_diagram.py
python generators\generate_figure_5_multinode.py
python generators\generate_sinr_heatmap.py
python generators\generate_figure_1b_fspl_comparison.py
python generators\generate_figure7_multinode.py
python generators\generate_figure_9b_scintillation_comparison.py
python generators\generate_sinr_table.py
python generators\generate_pathloss_table.py
python generators\generate_relay_table.py
python generators\generate_uav_relay_table.py
python generators\generate_atm_loss_tables.py
python generators\generate_figures.py
python generators\generate_phase2_figures.py
```

### 4c. Not covered by the master script, but referenced by the paper

Three figures embedded in `HAPS_AI_HW_ChannelModel.tex` come from scripts under
`src/plots/` that `generate_all_wsl.sh` does not call:

```powershell
python plots\plot_atmospheric_losses_frequency.py   # -> fig_atm_loss_nominal_frequency.png (+ worst-case variant)
python plots\sinr_plot.py                             # -> haps_sinr_trellis.png, haps_feeder_link_38ghz.png
```

`sinr_plot.py`'s `__main__` block reads two CSVs
(`haps_sinr_data_2ghz_service_fixed.csv`, `haps_feeder_link_38ghz_fixed.csv`) that
are **not currently produced by any script in this repo** — they must exist in the
working directory already (from a prior/manual export) or be regenerated by
whatever originally created them before this script will run. Check for them
before relying on this step.

`network_diagram.pdf` is compiled separately from LaTeX, not Python:

```powershell
cd src\plots
pdflatex -interaction=nonstopmode network_diagram.tex
```

## 5. Figure-to-source mapping (verified against `savefig`/`to_csv` calls)

| Output file | Produced by |
|---|---|
| `3_uav_pathloss.png`, `4_sinr.png`, `figure5_model_received_power.png` | `models/channel_model.py` |
| `9a_scintillation_fade_vs_time.png`, `9b_scintillation_fade_vs_elev.png` | `models/channel_model.py` |
| `10a_feeder_loss_vs_distance.png`, `10b_scintillation_margin.png` | `models/channel_model.py` |
| `11a-d_fading_envelope_timeseries.png` | `models/channel_model.py` |
| `1b_haps_fspl_2ghz_vs_38ghz.png` | `generators/generate_figure_1b_fspl_comparison.py` |
| `constellation_with_sectors.png` | `generators/generate_constellation_diagram.py` |
| `figure5_multi_haps_sinr_mean.png` | `generators/generate_figure_5_multinode.py` |
| `figure7_multi_haps_received_power.png` | `generators/generate_figure7_multinode.py` (not currently embedded in the paper) |
| `sinr_heatmap_spatial.png` | `generators/generate_sinr_heatmap.py` |
| `sinr_multinode_spatial_table.csv`, `sinr_spatial_analysis_summary.csv`, `sinr_table_*deg.csv` | `generators/generate_sinr_table_2d_spatial.py` |
| Path-loss appendix table (`Path_loss_comparison_2ghz_38ghz.tex/.csv`) | `generators/generate_pathloss_table.py` |
| SINR appendix table (`SINR_multinode_table_distances.tex/.csv`) | `generators/generate_sinr_table.py` |
| Atmospheric-loss appendix tables (`atm_losses_nominal.tex`, `atm_losses_worstcase.tex`) | `generators/generate_atm_loss_tables.py` |
| `fig_atm_loss_nominal_frequency.png` (+ worst-case) | `plots/plot_atmospheric_losses_frequency.py` (Section 4c — not in the master script) |
| `haps_sinr_trellis.png`, `haps_feeder_link_38ghz.png` | `plots/sinr_plot.py` (Section 4c — not in the master script, needs pre-existing CSVs) |
| `network_diagram.pdf` | `plots/network_diagram.tex` via `pdflatex` (Section 4c) |
| `system_topology.*`, `elevation_los_probability.*`, `rain_attenuation_curve.*`, `link_budget_summary.*` | `generators/generate_figures.py` — an older figure set, not currently referenced by any `\includegraphics` in the paper |
| `fig_battery_profile_24h.*`, `fig_reward_landscape.*`, `fig_observation_space.*` | `generators/generate_phase2_figures.py` — Phase 2 material, see the Phase 2 guide |

## 6. Copying outputs into the paper and compiling

Generators write to `src/output/`; the paper reads from `figures/` and
`appendix_tables/` at the repo root:

```powershell
cd C:\Github\haps_ground_communications
Copy-Item src\output\*.png figures\ -Force
Copy-Item src\output\*.csv, src\output\*.tex appendix_tables\ -Force
```

Then compile:

```powershell
.\build-paper.bat
```

(`build-paper.bat` runs `pdflatex` twice, which is what `HAPS_AI_HW_ChannelModel.tex`
needs to resolve its cross-references and table of contents.)

## 7. Recommended developer workflow

1. Run `channel_model.py` and `battery_model.py` first — several downstream
   generators read the constellation geometry and CSVs they depend on
   transitively via `models.channel_model`.
2. Run `generate_sinr_table_2d_spatial.py` before `generate_constellation_diagram.py`,
   `generate_figure_5_multinode.py`, or `generate_sinr_heatmap.py` — those three
   read the CSV it writes (`src/output/sinr_multinode_spatial_table.csv`).
3. Run the remaining `src/generators/` scripts (order-independent otherwise).
4. If you need `fig_atm_loss_nominal_frequency.png`, `haps_sinr_trellis.png`,
   `haps_feeder_link_38ghz.png`, or `network_diagram.pdf`, run the Section 4c steps
   manually — the master script does not produce them.
5. Copy `src/output/*` into `figures/` and `appendix_tables/` (Section 6), then run
   `build-paper.bat` and check the PDF for missing-figure placeholders or
   `??` cross-references, which mean a generator was skipped or a file wasn't
   copied.
6. For the DRL association baseline referenced in Section III.D/IV.D
   (`tab:assoc-baseline-results`), see
   [`docs/PHASE2_RUN_GUIDE.md`](PHASE2_RUN_GUIDE.md) Section 6 — that table is
   produced by `eval_baseline_association.py`, not by anything in this guide.
