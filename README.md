# drift-routing

Data and scripts for the paper *Runtime drift breaks static energy profiles:
a measurement study and a survival-constrained router*.

All seven data figures and all four tables in the paper are produced from the
CSV files in `data/`. Nothing is typed by hand into the LaTeX.

## Running it

```
pip install -r requirements.txt
make
```

This writes the figures to `figures/`, the tables to `tables/`, and then runs
`src/verify.py`, which should end with:

```
81/81 checks passed.
```

Other targets: `make figures`, `make tables`, `make verify` (lists every
check), `make clean`. Without make, `python3 src/make_all.py` does the same
thing.

Tested on Python 3.11 with matplotlib 3.10 and numpy 2.4.

## Layout

```
data/        14 CSV files, one per figure panel or table
src/         figure scripts, table generator, verifier
figures/     generated PDF and PNG
tables/      generated LaTeX fragments
simulator/   the discrete-event simulator that produced data/
```


| Script                          | Figure      | Input                             |
| ------------------------------- | ----------- | --------------------------------- |
| `fig07_static_baselines.py`     | 7           | `fig07_static_baselines.csv`      |
| `fig08_saving_under_drift.py`   | 8           | `fig08_saving_under_drift.csv`    |
| `fig09_rank_inversions.py`      | 9           | `fig09a_*.csv`, `fig09b_*.csv`    |
| `fig10_reprofiling_cost.py`     | 10          | `table3_reprofiling.csv`          |
| `fig11_budget_adherence.py`     | 11          | `fig11a_*.csv`, `fig11b_*.csv`    |
| `fig12_staleness_robustness.py` | 12          | `fig12a_*.csv`, `fig12b_*.csv`    |
| `fig13_sensitivity.py`          | 13          | `fig13a_*.csv`, `fig13b_*.csv`    |
| `make_tables.py`                | Tables I-IV | `table1_*.csv` ... `table4_*.csv` |

Figures 1 to 6 of the paper are schematics and are not generated here.

## Using the output

The figures are vector PDF with fonts embedded, sized for IEEEtran at the
width each one is used at:

```latex
\includegraphics[width=\columnwidth]{figures/fig08_saving_under_drift.pdf}
```


The tables are complete floats and need `\usepackage{booktabs}`:

```latex
\input{tables/table2_mechanism_ablation}
```

Tables I and II fit one column. Tables III and IV are wide and use `table*`,
so they span both columns.

## simulator/

The discrete-event simulator that produced `data/`. It runs on its own:

```
python3 simulator/run.py --smoke              # one short run
python3 simulator/sweep.py --smoke --jobs 4   # every sweep, short
```

`--smoke` uses a synthetic example profile table so the code runs on a clean
clone. To reproduce the paper, put the measured 72-pair table at
`simulator/profiles/profile_table.csv` and drop `--smoke`.
`simulator/README.md` covers the fleet and drift models, the routing arms,
the fixed constants and the run-summary fields; `simulator/profiles/README.md`
covers the table format and says exactly what the synthetic one does and does
not reproduce.

`sweep.py` writes the `data/*.csv` this repository reads, so a re-run feeds
straight back into `make`. It refuses to overwrite `data/` without `--force`,
since that directory holds the released results.

Nothing outside `simulator/` depends on it: `data/` already holds the outputs
for every configuration in the paper.

## Notes

- Results are 10 seeds per configuration, 5 per cell in Fig. 13(a) and 3 per
  cell in Fig. 13(b). Bands are mean plus or minus one SD and are stored as
  absolute values, so no plot recomputes them.
- `figures/` and `tables/` are committed so the repository is readable without
  running anything. `.gitignore` has the lines to stop tracking them.

## Licence

MIT, see `LICENSE`. If you use this, please cite the paper (`CITATION.cff`).
