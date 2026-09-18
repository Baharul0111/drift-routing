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

| Script | Figure | Input |
| --- | --- | --- |
| `fig07_static_baselines.py` | 7 | `fig07_static_baselines.csv` |
| `fig08_saving_under_drift.py` | 8 | `fig08_saving_under_drift.csv` |
| `fig09_rank_inversions.py` | 9 | `fig09a_*.csv`, `fig09b_*.csv` |
| `fig10_reprofiling_cost.py` | 10 | `table3_reprofiling.csv` |
| `fig11_budget_adherence.py` | 11 | `fig11a_*.csv`, `fig11b_*.csv` |
| `fig12_staleness_robustness.py` | 12 | `fig12a_*.csv`, `fig12b_*.csv` |
| `fig13_sensitivity.py` | 13 | `fig13a_*.csv`, `fig13b_*.csv` |
| `make_tables.py` | Tables I-IV | `table1_*.csv` ... `table4_*.csv` |

Figures 1 to 6 of the paper are schematics and are not generated here.

## Using the output

The figures are vector PDF with fonts embedded, sized for IEEEtran at the
width each one is used at:

```latex
\includegraphics[width=\columnwidth]{figures/fig08_saving_under_drift.pdf}
```

If you change that width, scale `FS` in `src/common.py` by the same factor.
Every font size in the scripts derives from it, and it is set against the
7 pt floor in the IEEE style guide.

The tables are complete floats and need `\usepackage{booktabs}`:

```latex
\input{tables/table2_mechanism_ablation}
```

Tables I and II fit one column. Tables III and IV are wide and use `table*`,
so they span both columns.

## verify.py

The risk with an artifact like this is that the repository and the PDF stop
agreeing after a late correction. `src/verify.py` tests the data against what
the paper says about it rather than against a stored copy of itself, and names
the source of each check:

```
PASS  Sec. VII-A               20.2% energy reduction vs HMG (computed 20.2%)
PASS  Table II                 all three together produce 3.50% inversions
PASS  Fig. 11(b) vs Table IV   all 12 Fig. 11(b) points match the Table IV
                               overshoot column
```

There are four kinds of check:

1. Values the results section quotes in prose (2.19 Wh, 33.7 mAP, 9.7%,
   57.7% to 61.2%).
2. Values the paper computes rather than reports: the 20.2% reduction, the
   0.8 mAP it costs, the net-gain labels in Fig. 10.
3. Agreement between artifacts: the twelve points Fig. 11(b) shares with
   Table IV, and Fig. 10's bars against Table III's columns.
4. Structural claims: thermal throttling alone inverts nothing (Corollary 1);
   the joint inversion rate exceeds the sum of the individual effects; exactly
   one re-profiling policy pays for itself; greedy's energy does not depend on
   the budget; every significance mark agrees with its own interval.

A failure prints the claim, where in the paper it lives, and the value that
came out instead.

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
