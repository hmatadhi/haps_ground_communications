# Figure generation source inventory

This directory is intended to hold the Python source files that generate the paper figures and any supporting dependency modules.

## Purpose

The files listed here are the sources that produce the plots and tables referenced by the paper. They should live under `./src` so the project has a single, clear place for figure-generation logic.

## Files to place under ./src

### SINR and multi-node figures

- `generate_figure_5_multinode.py` — Figure 5 (multi-HAPS interference SINR)
- `generate_figure7_multinode.py` — Figure 7 (SINR patterns across constellation)
- `sinr_plot.py` — SINR trellis / pattern plot
- `sinr_plot_with_los.py` — SINR plot including LOS behavior
- `generate_sinr_heatmap.py` — SINR heatmap generation
- `generate_sinr_table.py` — SINR data table generation
- `generate_sinr_table_2d_spatial.py` — 2D spatial SINR table generation

### Path loss figures

- `generate_figure_1b_fspl_comparison.py` — Figure 1b (2 GHz vs 38 GHz FSPL)
- `generate_pathloss_table.py` — Path loss comparison tables

### Atmospheric loss figures

- `plot_atmospheric_losses_frequency.py` — Atmospheric losses vs frequency (Figure with `atm_loss_nominal`)
- `generate_atm_loss_tables.py` — Atmospheric loss breakdown tables

### Scintillation figures

- `generate_figure_9b_scintillation_comparison.py` — Figure 9b (scintillation vs elevation)
- `replot_variants.py` — Scintillation time-series variants (11a-d)

### Constellation and network

- `generate_constellation_diagram.py` — Figure 6 (constellation geometry with sectors)
- `network_diagram.pdf` — generated from LaTeX .tex sources

### General and utility scripts

- `generate_figures.py` — main figure generation orchestrator
- `generate_phase2_figures.py` — phase 2 figure outputs
- `compact_tables.py` — compact summary tables
- `table_b1_scenarios.py` — Appendix B scenario tables
- `make_seed_figure.py` — seed/reference figure

## Figure-to-source mapping

The following mappings were identified from the project list:

- `1b_haps_fspl_2ghz_vs_38ghz.png` → `generate_figure_1b_fspl_comparison.py`
- `5_multi_node_sinr.png` → `generate_figure_5_multinode.py`
- `9b_scintillation_fade_vs_elev.png` → `generate_figure_9b_scintillation_comparison.py`
- `11a-d_fading_envelope_timeseries.png` → `replot_variants.py`
- `constellation_with_sectors.png` → `generate_constellation_diagram.py`
- `fig_atm_loss_nominal_frequency.png` → `plot_atmospheric_losses_frequency.py`
- `haps_sinr_trellis.png` → `sinr_plot.py` and/or `sinr_plot_with_los.py`

## Recommended dependency layout

Place all generated figure source scripts under this directory and keep any shared helper modules nearby, for example:

- `src/` — primary source scripts
- `src/utils/` — common plotting and data utilities
- `src/data/` — generated or cached intermediate data files, if needed

## Notes

- This directory is a project-local staging area for figure-generation sources.
- The actual files can be copied from the upstream AI-HAPS repository into this directory and kept version-controlled here for the paper build workflow.
- The paper itself remains built via `build-paper.bat`; CMake is reserved for later generation orchestration.
