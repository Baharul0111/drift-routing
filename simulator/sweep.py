#!/usr/bin/env python3
# Run a grid of configurations over seeds and write ../data/*.csv.
#
#   python3 sweep.py --profiles profiles/profile_table.csv --seeds 10
#   python3 sweep.py --only fig08 --seeds 10 --jobs 4
#
# Every figure and table in the paper has a sweep here, and each one writes
# the CSV that src/ reads, with the column names data/README.md documents.
# After a sweep, `make` in the repository root redraws the paper.

import argparse
import csv
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from driftsim import ProfileTable, RunConfig, Simulation
from driftsim import stats
from driftsim.profiles import default_table_path

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), 'data')

TABLE = None          # set in main, shared by the worker processes


def _run(kw):
    return Simulation(TABLE, RunConfig(**kw)).run()


def _init(path, ):
    global TABLE
    TABLE = ProfileTable.load(path)


def run_many(pool, kwargs_list):
    if pool is None:
        return [_run(kw) for kw in kwargs_list]
    return pool.map(_run, kwargs_list)


def write(name, header, rows):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name + '.csv'), 'w', newline='',
              encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print('  %s.csv  %d rows' % (os.path.join(os.path.basename(DATA), name), len(rows)))


def band(values):
    """-> (mean, mean - sd, mean + sd) over seeds."""
    m = stats.mean(values)
    s = stats.sd(values)
    return m, m - s, m + s


def r4(x):
    return round(x, 4)


# ---------------------------------------------------------------- Fig. 7 --
def fig07(pool, seeds, base):
    arms = [('round_robin', 'Round robin', 0), ('random', 'Random', 0),
            ('LE', 'LE', 0), ('LI', 'LI', 0), ('HM', 'HM', 0),
            ('HMG', 'HMG', 0)]
    ecore = [('oracle', 'ECORE (oracle)'), ('ed', 'ECORE (ED)'),
             ('sf', 'ECORE (SF)'), ('ob', 'ECORE (OB)')]

    jobs, meta = [], []
    for arm, label, _ in arms:
        for s in seeds:
            jobs.append(dict(base, arm=arm, seed=s, mechanisms=()))
            meta.append((label, 0))
    for est, label in ecore:
        for s in seeds:
            jobs.append(dict(base, arm='greedy', estimator=est, seed=s,
                             mechanisms=()))
            meta.append((label, 1))

    res = run_many(pool, jobs)
    agg = {}
    for (label, is_ec), r in zip(meta, res):
        agg.setdefault(label, (is_ec, [], [], []))
        agg[label][1].append(r['energy_mWh'])
        agg[label][2].append(r['mAP'])
        agg[label][3].append(r['latency_ms'])

    order = [a[1] for a in arms] + [e[1] for e in ecore]
    rows = []
    for label in order:
        is_ec, e, a, l = agg[label]
        rows.append([label, is_ec, r4(stats.mean(e)), r4(stats.mean(a)),
                     r4(stats.mean(l))])
    write('fig07_static_baselines',
          ['policy', 'is_ecore', 'energy_mWh', 'mAP', 'latency_ms'], rows)


# ------------------------------------------------------- Figs. 8 and 9 ----
def fig08_09(pool, seeds, base):
    ests = [('oracle', 'ECORE (oracle)'), ('ed', 'ECORE (ED)'),
            ('ob', 'ECORE (OB)')]

    ref_jobs = [dict(base, arm='HMG', seed=s) for s in seeds]
    ref = run_many(pool, ref_jobs)

    by_seed = dict(zip(seeds, ref))

    jobs, meta = [], []
    for est, label in ests:
        for s in seeds:
            jobs.append(dict(base, arm='greedy', estimator=est, seed=s))
            meta.append((label, s))
    res = run_many(pool, jobs)

    saving, invrate, penalty = {}, {}, {}
    for (label, seed), r in zip(meta, res):
        hmg = by_seed[seed]
        for k, w in enumerate(r['windows']):
            hw = hmg['windows'][k]
            t = round(w['t_min'])
            s_pct = 100.0 * (hw['energy_mWh'] - w['energy_mWh']) \
                / hw['energy_mWh'] if hw['energy_mWh'] else 0.0
            saving.setdefault((label, t), []).append(s_pct)
            invrate.setdefault((label, t), []).append(w['inversion_rate_pct'])
            penalty.setdefault((label, t), []).append(w['energy_penalty_mWh'])

    def emit(name, src, ycol):
        rows = []
        for _est, label in ests:
            ts = sorted(set(t for (l, t) in src if l == label))
            for t in ts:
                m, lo, hi = band(src[(label, t)])
                rows.append([label, t, r4(m), r4(lo), r4(hi)])
        write(name, ['estimator', 'elapsed_min', ycol, 'sd_lo', 'sd_hi'], rows)

    emit('fig08_saving_under_drift', saving, 'saving_pct')
    emit('fig09a_inversion_rate', invrate, 'inversion_rate_pct')
    emit('fig09b_energy_penalty', penalty, 'energy_penalty_mWh')


# ------------------------------------------- Table III (and so Fig. 10) ---
def table3(pool, seeds, base):
    specs = [('never', 'Never', ''),
             ('fixed:1800', 'Fixed 1800 s', 'Fixed 1800s'),
             ('fixed:600', 'Fixed 600 s', 'Fixed 600s'),
             ('fixed:180', 'Fixed 180 s', 'Fixed 180s'),
             ('fixed:60', 'Fixed 60 s', 'Fixed 60s'),
             ('staleness:0.08', 'Staleness 0.08', 'UCB 0.08'),
             ('staleness:0.03', 'Staleness 0.03', 'UCB 0.03'),
             ('staleness:0.01', 'Staleness 0.01', 'UCB 0.01'),
             ('staleness:0.005', 'Staleness 0.005', 'UCB 0.005')]

    jobs = []
    for spec, _, _ in specs:
        for s in seeds:
            jobs.append(dict(base, arm='greedy', seed=s, reprofile=spec))
    res = run_many(pool, jobs)

    n = len(seeds)
    per = [res[i * n:(i + 1) * n] for i in range(len(specs))]
    never = [r['regret_mWh'] for r in per[0]]

    raw = []
    for i, (spec, label, figlab) in enumerate(specs):
        probe = stats.mean([r['probe_mWh'] for r in per[i]])
        regret = [r['regret_mWh'] for r in per[i]]
        if i == 0:
            raw.append([label, figlab, r4(probe), r4(stats.mean(regret)),
                        '', '', '', None])
            continue
        d, lo, hi = stats.paired_ci(regret, never)
        p = stats.wilcoxon_p(regret, never)
        raw.append([label, figlab, r4(probe), r4(stats.mean(regret)),
                    r4(d), r4(lo), r4(hi), p])

    ps = [row[7] for row in raw if row[7] is not None]
    keep = stats.holm(ps)
    k = 0
    rows = []
    for row in raw:
        if row[7] is None:
            rows.append(row[:7] + [''])
        else:
            rows.append(row[:7] + ['*' if keep[k] else ''])
            k += 1
    write('table3_reprofiling',
          ['policy', 'fig_label', 'probe_mWh', 'regret_mWh',
           'delta_regret_mWh', 'ci_lo', 'ci_hi', 'significant'], rows)


# ------------------------------------------- Table II, mechanism ablation -
def table2(pool, seeds, base):
    sets = [(('thermal',), 'Thermal only'),
            (('contention',), 'Contention only'),
            (('battery',), 'Battery only'),
            (('thermal', 'contention', 'battery'), 'All three')]
    jobs = []
    for mech, _ in sets:
        for s in seeds:
            jobs.append(dict(base, arm='greedy', seed=s, mechanisms=mech))
    res = run_many(pool, jobs)
    n = len(seeds)
    rows = []
    for i, (_, label) in enumerate(sets):
        grp = res[i * n:(i + 1) * n]
        rows.append([label,
                     round(stats.mean([r['energy_Wh'] for r in grp]), 1),
                     round(stats.mean([r['inversion_rate'] for r in grp]), 4),
                     round(stats.mean([r['mAP'] for r in grp]), 2)])
    write('table2_mechanism_ablation',
          ['mechanism', 'energy_Wh', 'inversion_rate', 'mAP'], rows)


# ------------------------------------------- Fig. 11 and Table IV --------
FRACTIONS = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def fig11_table4(pool, seeds, base):
    ref = run_many(pool, [dict(base, arm='HMG', seed=s) for s in seeds])
    hmg = stats.mean([r['energy_mWh'] for r in ref])

    jobs, meta = [], []
    for f in FRACTIONS:
        for arm, label in [('greedy', 'Greedy'), ('lyapunov', 'Lyapunov')]:
            for s in seeds:
                jobs.append(dict(base, arm=arm, seed=s, budget_mWh=f * hmg))
                meta.append((f, arm, label))
    res = run_many(pool, jobs)

    dev, t4 = {}, {}
    for (f, arm, label), r in zip(meta, res):
        dev.setdefault((f, arm), []).append(r['final_overshoot_pct'])
        t4.setdefault((f, label), []).append(r)

    write('fig11b_budget_deviation',
          ['policy', 'budget_fraction', 'final_deviation_pct'],
          [[('Greedy (ECORE)' if a == 'greedy' else 'Lyapunov controller'),
            f, r4(stats.mean(dev[(f, a)]))]
           for a in ('greedy', 'lyapunov') for f in FRACTIONS])

    rows = []
    for f in FRACTIONS:
        for label in ('Greedy', 'Lyapunov'):
            grp = t4[(f, label)]
            rows.append([f, label,
                         round(stats.mean([r['energy_Wh'] for r in grp]), 1),
                         round(stats.mean([r['final_overshoot_pct']
                                           for r in grp]), 1),
                         round(stats.mean([r['in_violation_pct']
                                           for r in grp]), 1),
                         round(stats.mean([r['mAP'] for r in grp]), 2)])
    write('table4_budget_adherence',
          ['budget_fraction', 'policy', 'energy_Wh', 'overshoot_pct',
           'in_violation_pct', 'mAP'], rows)

    # panel (a): one representative run at the 70% budget
    reps = run_many(pool, [
        dict(base, arm='greedy', seed=seeds[0], budget_mWh=0.7 * hmg),
        dict(base, arm='lyapunov', seed=seeds[0], budget_mWh=0.7 * hmg)])
    rows = []
    for r, label in zip(reps, ('Greedy (ECORE)', 'Lyapunov controller')):
        for t_min, e in r['cumulative']:
            rows.append([label, r4(t_min), r4(e)])
    H = base['horizon_s'] / 60.0
    for t_min, _ in reps[0]['cumulative']:
        rows.append(['Budget envelope', r4(t_min), r4(0.7 * hmg * t_min / H)])
    write('fig11a_cumulative_energy',
          ['policy', 'elapsed_min', 'cumulative_energy_mWh'], rows)


# --------------------------------------------------------------- Fig. 12 --
BETAS = [0, 5, 10, 20, 30, 50]


def fig12(pool, seeds, base):
    ref = run_many(pool, [dict(base, arm='HMG', seed=s) for s in seeds])
    budget = 0.7 * stats.mean([r['energy_mWh'] for r in ref])

    jobs, meta = [], []
    for b in BETAS:
        for arm, label in [('greedy', 'Greedy (ECORE)'),
                           ('lyapunov', 'Lyapunov controller')]:
            for s in seeds:
                jobs.append(dict(base, arm=arm, seed=s, beta=b / 100.0,
                                 budget_mWh=budget))
                meta.append((b, label))
    res = run_many(pool, jobs)

    over, acc = {}, {}
    for (b, label), r in zip(meta, res):
        over.setdefault((label, b), []).append(r['final_overshoot_pct'])
        acc.setdefault((label, b), []).append(r['mAP'])

    def emit(name, src, ycol):
        rows = []
        for label in ('Greedy (ECORE)', 'Lyapunov controller'):
            for b in BETAS:
                m, lo, hi = band(src[(label, b)])
                rows.append([label, b, r4(m), r4(lo), r4(hi)])
        write(name, ['policy', 'beta_pct', ycol, 'sd_lo', 'sd_hi'], rows)

    emit('fig12a_budget_overshoot', over, 'final_overshoot_pct')
    emit('fig12b_accuracy_cost', acc, 'mean_mAP')


# --------------------------------------------------------------- Fig. 13 --
R_THS = [2.5, 4, 5.5, 7, 8.5]
K_THRS = [0.01, 0.025, 0.04, 0.055, 0.07]
CAPS = [0.5, 1.0, 2.0]
SAGS = [0.0, 0.22, 0.33]


def fig13(pool, seeds, base):
    cells = seeds[:5] or seeds
    ref = run_many(pool, [dict(base, arm='HMG', seed=s) for s in cells])
    hmg = dict((s, r['energy_mWh']) for s, r in zip(cells, ref))

    jobs, meta = [], []
    for k in K_THRS:
        for R in R_THS:
            for s in cells:
                jobs.append(dict(base, arm='greedy', seed=s, R_th=R, k_thr=k))
                meta.append((k, R, s))
    res = run_many(pool, jobs)
    grid = {}
    for (k, R, s), r in zip(meta, res):
        grid.setdefault((k, R), []).append(
            100.0 * (hmg[s] - r['energy_mWh']) / hmg[s])
    write('fig13a_thermal_grid',
          ['k_thr'] + ['R_th_%g' % R for R in R_THS],
          [[k] + [round(stats.mean(grid[(k, R)]), 1) for R in R_THS]
           for k in K_THRS])

    cells3 = seeds[:3] or seeds
    jobs, meta = [], []
    for a in SAGS:
        for c in CAPS:
            for s in cells3:
                jobs.append(dict(base, arm='greedy', seed=s, sag_a=a,
                                 cap_scale=c))
                meta.append((a, c))
    res = run_many(pool, jobs)
    grid = {}
    for (a, c), r in zip(meta, res):
        grid.setdefault((a, c), []).append(r['late_inversion_rate_pct'])
    write('fig13b_battery_grid',
          ['sag_a'] + ['cap_%gx' % c for c in CAPS],
          [[a] + [round(stats.mean(grid[(a, c)]), 1) for c in CAPS]
           for a in SAGS])


SWEEPS = {
    'fig07': fig07,
    'fig08': fig08_09,
    'fig09': fig08_09,
    'table2': table2,
    'table3': table3,
    'fig11': fig11_table4,
    'table4': fig11_table4,
    'fig12': fig12,
    'fig13': fig13,
}
ORDER = ['fig07', 'fig08', 'table2', 'table3', 'fig11', 'fig12', 'fig13']


def main():
    ap = argparse.ArgumentParser(description='run the paper\'s sweeps')
    ap.add_argument('--profiles', default=None)
    ap.add_argument('--seeds', type=int, default=10)
    ap.add_argument('--jobs', type=int, default=1)
    ap.add_argument('--horizon', type=float, default=7200.0)
    ap.add_argument('--arrival-rate', type=float, default=30.0)
    ap.add_argument('--only', action='append', default=None,
                    help='run only these sweeps (repeatable): %s'
                         % ', '.join(ORDER))
    ap.add_argument('--smoke', action='store_true',
                    help='2 seeds, 10-minute horizon, example table')
    ap.add_argument('--out-dir', default=None,
                    help='where to write the CSVs (default: ../data)')
    ap.add_argument('--force', action='store_true',
                    help='allow overwriting ../data, which holds the '
                         'released results')
    args = ap.parse_args()

    global DATA
    released = os.path.abspath(os.path.join(os.path.dirname(HERE), 'data'))
    DATA = os.path.abspath(args.out_dir) if args.out_dir else released
    if DATA == released and not args.force:
        raise SystemExit(
            'This would overwrite ../data, which holds the results the paper\n'
            'reports. Write somewhere else with --out-dir, or pass --force if\n'
            'you mean to replace them.')

    path = args.profiles
    if path is None:
        if args.smoke:
            path = os.path.join(HERE, 'profiles', 'example_profile_table.csv')
        else:
            path = default_table_path()
            if not os.path.exists(path):
                raise SystemExit(
                    'no profile table at %s. Pass --profiles, or use --smoke.'
                    % path)
    if args.smoke:
        args.seeds = min(args.seeds, 2)
        args.horizon = min(args.horizon, 600.0)

    base = dict(horizon_s=args.horizon, arrival_rate=args.arrival_rate,
                window_s=max(args.horizon / 12.0, 30.0))
    seeds = list(range(args.seeds))

    pool = None
    if args.jobs > 1:
        pool = Pool(args.jobs, initializer=_init, initargs=(path,))
    _init(path)

    names = args.only or ORDER
    for name in names:
        if name not in SWEEPS:
            raise SystemExit('unknown sweep: %s' % name)
        print('[%s]' % name)
        SWEEPS[name](pool, seeds, base)

    if pool is not None:
        pool.close()
        pool.join()
    print('\nDone. Run `make` in the repository root to redraw the paper.')


if __name__ == '__main__':
    main()
