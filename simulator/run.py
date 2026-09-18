#!/usr/bin/env python3
# One configuration, one run summary.
#
#   python3 run.py --arm lyapunov --seed 0 --budget-fraction 0.7 \
#                  --profiles profiles/profile_table.csv --out runs/l0.json
#
# --smoke runs a short configuration against the synthetic example table, to
# check the code paths without needing the measured profile table.

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from driftsim import ProfileTable, RunConfig, Simulation
from driftsim.profiles import default_table_path


def build_parser():
    p = argparse.ArgumentParser(description='drift-aware routing simulator')
    p.add_argument('--arm', default='greedy',
                   help='round_robin, random, LE, LI, HM, HMG, greedy, '
                        'lyapunov')
    p.add_argument('--estimator', default='oracle',
                   help='oracle, ed, ob, sf')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--horizon', type=float, default=7200.0, dest='horizon_s')
    p.add_argument('--arrival-rate', type=float, default=30.0)
    p.add_argument('--window', type=float, default=600.0, dest='window_s')
    p.add_argument('--mechanisms', default='thermal,contention,battery',
                   help='comma separated, or "none"')
    p.add_argument('--delta-map', type=float, default=5.0, dest='delta_mAP')
    p.add_argument('--epsilon', type=float, default=0.01)
    p.add_argument('--tau-q', type=float, default=0.15)
    p.add_argument('--V', type=float, default=1.0,
                   help='accuracy/energy trade-off; larger V keeps\n                        more accuracy and tracks the budget less tightly')
    p.add_argument('--reserve', type=float, default=0.02,
                   help='fraction of the budget held back')
    p.add_argument('--beta', type=float, default=0.0,
                   help='profile staleness bound, as a fraction')
    p.add_argument('--budget-fraction', type=float, default=None,
                   help='budget as a fraction of the HMG energy')
    p.add_argument('--budget-mWh', type=float, default=None)
    p.add_argument('--hmg-energy', type=float, default=None,
                   help='reference HMG energy for --budget-fraction; pass it '
                        'to skip the extra reference run')
    p.add_argument('--reprofile', default='never',
                   help='never, fixed:<seconds>, staleness:<threshold>')
    p.add_argument('--probe-cost', type=float, default=0.6,
                   dest='probe_cost_mWh')
    p.add_argument('--R-th', type=float, default=5.5)
    p.add_argument('--k-thr', type=float, default=0.04)
    p.add_argument('--sag-a', type=float, default=0.22)
    p.add_argument('--cap-scale', type=float, default=1.0)
    p.add_argument('--kappa-max', type=float, default=1.25)
    p.add_argument('--pool-size', type=int, default=14)
    p.add_argument('--replay', default=None,
                   help='path to a COCO-style object-count file')
    p.add_argument('--profiles', default=None,
                   help='profile table CSV (default: profiles/profile_table.csv)')
    p.add_argument('--out', default=None, help='write the summary JSON here')
    p.add_argument('--quiet', action='store_true')
    p.add_argument('--smoke', action='store_true',
                   help='short run against the synthetic example table')
    return p


def resolve_table(args):
    if args.profiles:
        return args.profiles
    if args.smoke:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, 'profiles', 'example_profile_table.csv')
    path = default_table_path()
    if not os.path.exists(path):
        raise SystemExit(
            'no profile table at %s.\n'
            'Put the measured table there, pass --profiles, or run with '
            '--smoke to use the synthetic example table.' % path)
    return path


def hmg_energy(table, args, cfg_kw):
    """Reference energy for --budget-fraction: HMG at the same seed."""
    kw = dict(cfg_kw)
    kw['arm'] = 'HMG'
    kw['budget_mWh'] = None
    kw['budget_fraction'] = None
    return Simulation(table, RunConfig(**kw)).run()['energy_mWh']


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.smoke:
        args.horizon_s = min(args.horizon_s, 600.0)
        args.window_s = min(args.window_s, 120.0)

    mech = () if args.mechanisms.strip().lower() in ('none', '') \
        else tuple(m.strip() for m in args.mechanisms.split(',') if m.strip())

    table = ProfileTable.load(resolve_table(args))

    kw = dict(arm=args.arm, estimator=args.estimator, seed=args.seed,
              horizon_s=args.horizon_s, arrival_rate=args.arrival_rate,
              window_s=args.window_s, mechanisms=mech,
              delta_mAP=args.delta_mAP, epsilon=args.epsilon,
              tau_q=args.tau_q, V=args.V, beta=args.beta,
              reprofile=args.reprofile, probe_cost_mWh=args.probe_cost_mWh,
              R_th=args.R_th, k_thr=args.k_thr, sag_a=args.sag_a,
              cap_scale=args.cap_scale, kappa_max=args.kappa_max,
              pool_size=args.pool_size, replay=args.replay,
              reserve=args.reserve)

    budget = args.budget_mWh
    if budget is None and args.budget_fraction is not None:
        ref = args.hmg_energy
        if ref is None:
            ref = hmg_energy(table, args, kw)
        budget = args.budget_fraction * ref
    kw['budget_mWh'] = budget
    if args.budget_fraction is not None:
        kw['budget_fraction'] = args.budget_fraction

    summary = Simulation(table, RunConfig(**kw)).run()
    summary['profile_table'] = os.path.basename(resolve_table(args))
    summary['n_pairs'] = table.n_pairs()

    if args.out:
        d = os.path.dirname(os.path.abspath(args.out))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(summary, fh, indent=1)

    if not args.quiet:
        keys = ['arm', 'estimator', 'seed', 'energy_Wh', 'mAP', 'latency_ms',
                'inversion_rate', 'probe_mWh', 'regret_mWh']
        if 'final_overshoot_pct' in summary:
            keys += ['final_overshoot_pct', 'in_violation_pct']
        for k in keys:
            v = summary[k]
            print('%-22s %s' % (k, ('%.4f' % v) if isinstance(v, float) else v))
    return summary


if __name__ == '__main__':
    main()
