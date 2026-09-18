# data

One CSV per figure panel and per table. Every number the paper prints is here.

## Conventions

- Energies are in mWh in the figure files and Wh in the table files, matching
  the unit each one prints. `verify.py` converts where it compares them.
- `sd_lo` and `sd_hi` are the mean plus or minus one SD over the 10 seeds,
  stored as absolute values so a plot does not have to add anything.
- `beta_pct` is the profile staleness bound in per cent.
- Inversion rates are a fraction in `table2_*` (0.0350) and a percentage in
  `fig09a_*` and `fig13b_*` (3.50), matching how each appears in the paper.
- The two `fig13*` files are grids: column 0 is the row's y value, the other
  column names carry the x values, and rows run bottom to top.

## Files

| File | Used by | Columns |
| --- | --- | --- |
| `fig07_static_baselines.csv` | Fig. 7 | `policy, is_ecore, energy_mWh, mAP, latency_ms` |
| `fig08_saving_under_drift.csv` | Fig. 8 | `estimator, elapsed_min, saving_pct, sd_lo, sd_hi` |
| `fig09a_inversion_rate.csv` | Fig. 9(a) | `estimator, elapsed_min, inversion_rate_pct, sd_lo, sd_hi` |
| `fig09b_energy_penalty.csv` | Fig. 9(b) | `estimator, elapsed_min, energy_penalty_mWh, sd_lo, sd_hi` |
| `fig11a_cumulative_energy.csv` | Fig. 11(a) | `policy, elapsed_min, cumulative_energy_mWh` |
| `fig11b_budget_deviation.csv` | Fig. 11(b) | `policy, budget_fraction, final_deviation_pct` |
| `fig12a_budget_overshoot.csv` | Fig. 12(a) | `policy, beta_pct, final_overshoot_pct, sd_lo, sd_hi` |
| `fig12b_accuracy_cost.csv` | Fig. 12(b) | `policy, beta_pct, mean_mAP, sd_lo, sd_hi` |
| `fig13a_thermal_grid.csv` | Fig. 13(a) | `k_thr, R_th_2.5 ... R_th_8.5` |
| `fig13b_battery_grid.csv` | Fig. 13(b) | `sag_a, cap_0.5x, cap_1x, cap_2x` |
| `table1_platform_thermal.csv` | Table I | `platform, u_thr_pct, m_max` |
| `table2_mechanism_ablation.csv` | Table II | `mechanism, energy_Wh, inversion_rate, mAP` |
| `table3_reprofiling.csv` | Table III and Fig. 10 | `policy, fig_label, probe_mWh, regret_mWh, delta_regret_mWh, ci_lo, ci_hi, significant` |
| `table4_budget_adherence.csv` | Table IV | `budget_fraction, policy, energy_Wh, overshoot_pct, in_violation_pct, mAP` |

## Two files feed two artifacts each

`table3_reprofiling.csv` is the only source for both Table III and Fig. 10.
The figure derives its bars rather than storing them again:

```
recovered = -delta_regret_mWh
net       = recovered - probe_mWh
CI half   = (ci_hi - ci_lo) / 2
```

`fig11b_budget_deviation.csv` and `table4_budget_adherence.csv` hold the same
comparison at the same six budget fractions. `verify.py` checks all twelve
points against each other.

## Provenance

These are simulator outputs over 10 seeds per configuration, 5 per cell in
Fig. 13(a) and 3 per cell in Fig. 13(b). Column names match the fields the run
summaries emit, so re-running an experiment overwrites these files in place.
