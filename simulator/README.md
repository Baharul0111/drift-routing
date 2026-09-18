# simulator

The discrete-event simulator behind `../data/`. It runs on its own; nothing
in the repository root depends on it, because `../data/` already holds the
outputs for every configuration in the paper.

```
python3 run.py --smoke                 # one short run, no setup needed
python3 sweep.py --smoke --jobs 4      # every sweep, short, to /tmp
```

`--smoke` uses `profiles/example_profile_table.csv`, which is synthetic.
To reproduce the paper, put the measured table at
`profiles/profile_table.csv` (see `profiles/README.md`) and drop `--smoke`.

## Layout

```
run.py              one configuration  -> one run summary (JSON)
sweep.py            a grid             -> ../data/*.csv
driftsim/
  engine.py         the event loop and the run summary
  profiles.py       the profile table and the candidate pool
  workload.py       Poisson arrivals, sticky object-count groups, replay
  models.py         thermal, contention, battery; the Table I thresholds
  estimators.py     oracle / ED / OB / SF content estimators
  routers.py        the static baselines, delta-mAP greedy, the controller
  reprofile.py      never / fixed-interval / staleness-triggered probing
  metrics.py        windowed energy, accuracy, inversions, regret
  stats.py          paired CIs, exact Wilcoxon, Holm
profiles/           the profile table, and a synthetic example one
```

## What it models

A six-node fleet (1 Jetson Orin Nano, 2 Raspberry Pi 5 + AI HAT+, 2
Raspberry Pi 5 + Coral TPU, 1 Raspberry Pi 4 + Coral TPU) serving Poisson
arrivals at 30 req/s over a two-hour horizon. The candidate pool is a
14-pair subset of the 72-pair table. Object-count groups follow a sticky
Markov stream; COCO-style annotation replay is available with `--replay`.

Three mechanisms move the true per-request cost while the router keeps
reading an unchanged profile:

| Mechanism | Parameters | Effect |
| --- | --- | --- |
| Thermal throttling | `u_thr`, `m_max` per platform (Table I), `R_th`, `k_thr` | latency and energy multiplier once sustained duty passes `u_thr`, capped at `m_max` |
| Contention | `kappa_max = 1.25` | a co-resident job inflates cost for the length of a burst |
| Battery efficiency sag | `a` (default 0.22), pack capacity | converter efficiency falls as the pack empties, `1/eta_min <= 1.43` |

Because every platform's `m_max` is below the 1.64x cross-device gap in the
profile, throttling on its own can never reorder the greedy choice. That is
Corollary 1, and the thermal-only row of Table II is its measurement.

## Fixed constants

```
horizon          7200 s
arrival rate     30 req/s, Poisson
fleet            6 nodes
candidate pool   14 pairs of 72
delta_mAP        5
epsilon          1 %          (Slater slack)
tau_q            0.15 s
seeds            10           (5 per cell in Fig. 13(a), 3 in Fig. 13(b))
probe cost c     0.6 mWh
```

## Routing arms

| `--arm` | Policy |
| --- | --- |
| `round_robin`, `random` | reference schedulers |
| `LE`, `LI` | lowest believed energy, lowest believed latency |
| `HM` | highest accuracy, single pair |
| `HMG` | highest accuracy spread over the nodes that can serve it; the reference for the energy saving in Fig. 8 |
| `greedy` | ECORE's policy: cheapest believed option within `delta_mAP` of the best |
| `lyapunov` | drift-plus-penalty, `argmin { Q * e_hat - V * mAP }`, with `Q` updated from realised energy |

Every arm sits on the same feasibility layer, in `routers.live_set`: the
`tau_q` latency constraint and node liveness. A comparison between arms is
therefore never a comparison of who was allowed to use a node whose pack had
already gone.

The last two rows are the paper's contrast. Nothing `greedy` computes is a
function of realised energy, so no budget can bind it at any staleness,
including zero. The controller reads believed energies but updates its queue
from realised ones, and that one asymmetry is what makes its budget
adherence uniform in the sign pattern of the profile error. `--V` prices
accuracy against energy: larger `V` keeps more accuracy and tracks the
budget less tightly. `--reserve` (default 0.02) holds a little back, because
the queue only pushes while it is positive, so a controller aimed exactly at
the budget settles slightly above it.

## Run summary

`run.py --out summary.json` writes a dict whose field names are the CSV
column names in `../data/README.md`: `energy_mWh`, `energy_Wh`, `mAP`,
`latency_ms`, `inversion_rate`, `inversion_rate_pct`,
`late_inversion_rate_pct`, `probe_mWh`, `regret_mWh`, and, when a budget is
set, `final_overshoot_pct` and `in_violation_pct`. It also carries
`windows` (per-window series, for Figs. 8, 9 and 13) and `cumulative` (for
Fig. 11(a)).

The `breakeven` block evaluates Theorem 3 on the run itself: the measured
inversion penalty against `c*K*H/D`, the threshold below which no probing
policy breaks even at any detection rate.

## Re-running a sweep

```
python3 sweep.py --profiles profiles/profile_table.csv --seeds 10 --jobs 8
```

`sweep.py` refuses to write over `../data` unless you pass `--force`, since
that directory holds the results the paper reports. Use `--out-dir` to write
elsewhere and compare first. After a sweep that you do mean to keep, `make`
in the repository root redraws every figure and table and re-runs the checks
in `src/verify.py`.

Individual sweeps: `--only fig07`, `fig08`, `table2`, `table3`, `fig11`,
`fig12`, `fig13` (repeatable).
