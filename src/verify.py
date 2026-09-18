# Check data/ against the values the paper states. Run with -v to list the
# checks that pass as well as the ones that fail. Exit 0 only if all pass.

import csv
import os
import sys

from common import DATA_DIR, FIG_DIR, group, load

VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv
RESULTS = []


def check(ok, what, where):
    RESULTS.append((bool(ok), what, where))


def near(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol


# Table I
t1 = {r['platform']: r for r in load('table1_platform_thermal')}
for plat, u, m in [('Raspberry Pi 5 + AI HAT+', 54.5, 1.50),
                   ('Raspberry Pi 5 + Coral TPU', 58.2, 1.50),
                   ('Raspberry Pi 5', 64.5, 1.67),
                   ('Raspberry Pi 4 + Coral TPU', 69.3, 1.54),
                   ('Jetson Orin Nano', 89.0, 1.37)]:
    r = t1[plat]
    check(near(float(r['u_thr_pct']), u, 0.05)
          and near(float(r['m_max']), m, 0.005),
          '%s: u_thr=%s%%, m_max=%s' % (plat, u, m), 'Table I')
check(t1['Raspberry Pi 3, Jetson Nano']['u_thr_pct'] == 'never',
      'Pi 3 and Jetson Nano never throttle at the evaluated duty cycles',
      'Table I')

# Fig. 7 and Sec. VII-A
f7 = {r['policy']: r for r in load('fig07_static_baselines')}
check(near(f7['LE']['energy_mWh'] / 1000, 2.19, 0.02),
      'LE attains the lowest energy, 2.19 Wh', 'Sec. VII-A')
check(near(f7['LE']['mAP'], 12.8, 0.05),
      'LE attains the lowest accuracy, 12.8 mAP', 'Sec. VII-A')
check(f7['LE']['energy_mWh'] == min(r['energy_mWh'] for r in f7.values()),
      'LE is the minimum-energy policy in the panel', 'Fig. 7(a)')
check(near(f7['HMG']['mAP'], 33.7, 0.05),
      'HMG attains the highest accuracy, 33.7 mAP', 'Sec. VII-A')
check(f7['HMG']['mAP'] == max(r['mAP'] for r in f7.values()),
      'HMG is the maximum-accuracy policy in the panel', 'Fig. 7(b)')
check(near(f7['HMG']['energy_mWh'] / 1000, 45.0, 0.05),
      'HMG costs 45.0 Wh', 'Sec. VII-A')
check(near(f7['ECORE (oracle)']['mAP'], 32.9, 0.05),
      'greedy/oracle reaches 32.9 mAP', 'Sec. VII-A')
check(near(f7['ECORE (oracle)']['energy_mWh'] / 1000, 35.9, 0.05),
      'greedy/oracle costs 35.9 Wh', 'Sec. VII-A')
red = ((f7['HMG']['energy_mWh'] - f7['ECORE (oracle)']['energy_mWh'])
       / f7['HMG']['energy_mWh'] * 100)
check(near(red, 20.2, 0.15),
      '20.2%% energy reduction vs HMG (computed %.1f%%)' % red, 'Sec. VII-A')
loss = f7['HMG']['mAP'] - f7['ECORE (oracle)']['mAP']
check(near(loss, 0.8, 0.15),
      'the reduction costs 0.8 mAP (computed %.2f)' % loss, 'Sec. VII-A')
check(near(f7['ECORE (OB)']['mAP'], 30.7, 0.05)
      and near(f7['ECORE (OB)']['energy_mWh'] / 1000, 36.1, 0.05),
      'the output-based estimator reaches 30.7 mAP at 36.1 Wh', 'Sec. VII-A')
check(f7['ECORE (SF)']['energy_mWh'] == max(r['energy_mWh']
                                            for r in f7.values()),
      'the SSD front end is the most expensive configuration', 'Sec. VII-A')

# Fig. 8 and Sec. VII-B
f8 = group(load('fig08_saving_under_drift'), 'estimator')


def window(name, lo_min, hi_min):
    return [r['saving_pct'] for r in f8[name]
            if lo_min <= r['elapsed_min'] <= hi_min]


for name, lo, hi in [('ECORE (oracle)', 19.6, 20.4),
                     ('ECORE (OB)', 15.7, 18.2),
                     ('ECORE (ED)', 15.0, 19.5)]:
    w = window(name, 0, 60)
    check(near(min(w), lo, 0.35) and near(max(w), hi, 0.35),
          'first-hour saving for %s is %s-%s%% (computed %.1f-%.1f%%)'
          % (name, lo, hi, min(w), max(w)), 'Sec. VII-B')
for name, lo, hi in [('ECORE (oracle)', 4.7, 6.5), ('ECORE (OB)', 1.5, 1.9)]:
    w = window(name, 65, 120)
    check(near(min(w), lo, 0.35) and near(max(w), hi, 0.35),
          'second-hour saving for %s is %s-%s%% (computed %.1f-%.1f%%)'
          % (name, lo, hi, min(w), max(w)), 'Sec. VII-B')
w = window('ECORE (ED)', 65, 120)
check(min(w) < 0 and near(min(w), -4.0, 0.4),
      'the edge-detection saving turns negative, reaching -4.0%% '
      '(computed %.1f%%)' % min(w), 'Sec. VII-B')
for name, avg in [('ECORE (oracle)', 15.2), ('ECORE (OB)', 11.8),
                  ('ECORE (ED)', 10.6)]:
    vals = window(name, 0, 999)
    got = sum(vals) / len(vals)
    check(near(got, avg, 0.6),
          'whole-horizon average saving for %s is %s%% (computed %.1f%%)'
          % (name, avg, got), 'Sec. VII-B')

# Fig. 9
f9 = group(load('fig09a_inversion_rate'), 'estimator')
last = {k: v[-1]['inversion_rate_pct'] for k, v in f9.items()}
check(near(last['ECORE (oracle)'], 9.7, 0.4),
      'the oracle inversion rate reaches 9.7%% at 120 min (computed %.1f%%)'
      % last['ECORE (oracle)'], 'Sec. VII-B')
coarse = max(last['ECORE (ED)'], last['ECORE (OB)'])
check(near(coarse, 10.9, 0.5),
      'the coarse estimators reach 10.9%% at 120 min (computed %.1f%%)'
      % coarse, 'Sec. VII-B')
check(all(v[0]['inversion_rate_pct'] < 1.5 for v in f9.values()),
      'every estimator starts the horizon below 1.5% inversions', 'Fig. 9(a)')
check(all(v[-1]['inversion_rate_pct'] > v[0]['inversion_rate_pct']
          for v in f9.values()),
      'inversions grow over the horizon for every estimator', 'Fig. 9(a)')

# Table II
t2 = {r['mechanism']: r for r in load('table2_mechanism_ablation')}
check(t2['Thermal only']['inversion_rate'] == 0.0,
      'thermal throttling alone produces no inversions (Corollary 1)',
      'Table II')
check(near(t2['Contention only']['inversion_rate'] * 100, 0.67, 0.005),
      'contention alone produces 0.67% inversions', 'Table II')
check(near(t2['Battery only']['inversion_rate'] * 100, 1.43, 0.005),
      'battery alone produces 1.43% inversions', 'Table II')
check(near(t2['All three']['inversion_rate'] * 100, 3.50, 0.005),
      'all three together produce 3.50% inversions', 'Table II')
parts = sum(t2[k]['inversion_rate'] for k in
            ('Thermal only', 'Contention only', 'Battery only'))
check(t2['All three']['inversion_rate'] > parts,
      'the joint rate (%.4f) exceeds the sum of the individual effects (%.4f)'
      % (t2['All three']['inversion_rate'], parts), 'Sec. VII-B')
check(near(t2['All three']['energy_Wh'], 43.0, 0.15),
      'the fleet consumes 43 Wh over two hours', 'Sec. VII-B')
check(near(t2['Thermal only']['mAP'], 32.9, 0.05)
      and near(t2['All three']['mAP'], 29.9, 0.05),
      'greedy mAP falls from 32.9 to 29.9 once battery effects are enabled',
      'Sec. VII-B')

# Table III and Fig. 10
t3 = {r['policy']: r for r in load('table3_reprofiling')}
check(near(t3['Never']['regret_mWh'], 105.1, 0.05),
      'the Never baseline carries 105.1 mWh of regret', 'Table III')
sig = set(k for k, r in t3.items() if r['significant'])
check(sig == set(['Staleness 0.01', 'Staleness 0.005']),
      'only the two tightest staleness policies are significant after Holm',
      'Table III')
for k, r in t3.items():
    if r['delta_regret_mWh'] is None:
        continue
    check(r['ci_lo'] <= r['delta_regret_mWh'] <= r['ci_hi'],
          '%s: the point estimate lies inside its own 95%% CI' % k, 'Table III')
    check((r['ci_lo'] > 0 or r['ci_hi'] < 0) == bool(r['significant']),
          '%s: the significance mark agrees with the CI crossing zero' % k,
          'Table III')
net = dict((k, (-r['delta_regret_mWh']) - r['probe_mWh'])
           for k, r in t3.items() if r['delta_regret_mWh'] is not None)
check(near(net['Staleness 0.005'], -1190.5, 0.6),
      "Fig. 10's worst net label is -1191 mWh (computed %.1f)"
      % net['Staleness 0.005'], 'Fig. 10')
check(near(net['Fixed 1800 s'], 6.0, 0.6),
      "Fig. 10's only clearly positive net label is +6 mWh (computed %.1f)"
      % net['Fixed 1800 s'], 'Fig. 10')
check(sum(1 for v in net.values() if v > 0) == 1,
      'exactly one re-profiling policy pays for itself', 'Sec. VII / Fig. 10')

# Table IV against Fig. 11(b)
t4 = load('table4_budget_adherence')
f11b = group(load('fig11b_budget_deviation'), 'policy')
NAME = {'Greedy': 'Greedy (ECORE)', 'Lyapunov': 'Lyapunov controller'}
bad = []
for r in t4:
    pt = next(p for p in f11b[NAME[r['policy']]]
              if abs(p['budget_fraction'] - r['budget_fraction']) < 1e-6)
    if not near(pt['final_deviation_pct'], r['overshoot_pct'], 0.15):
        bad.append((r['policy'], r['budget_fraction'], r['overshoot_pct'],
                    pt['final_deviation_pct']))
check(not bad,
      'all %d Fig. 11(b) points match the Table IV overshoot column%s'
      % (len(t4), (' -- mismatches: %s' % bad) if bad else ''),
      'Fig. 11(b) vs Table IV')
greedy = [r for r in t4 if r['policy'] == 'Greedy']
check(len(set(r['energy_Wh'] for r in greedy)) == 1
      and near(greedy[0]['energy_Wh'], 43.1, 0.05),
      'greedy ignores the budget: 43.1 Wh at every budget fraction', 'Table IV')
check(len(set(r['mAP'] for r in greedy)) == 1,
      "greedy's accuracy is likewise independent of the budget", 'Table IV')
lyap = [r for r in t4 if r['policy'] == 'Lyapunov']
check(all(r['overshoot_pct'] <= 2.0 for r in lyap),
      'the Lyapunov controller never overshoots a budget by more than 2%',
      'Table IV')
check(all(r['in_violation_pct'] <= 9.2 for r in lyap),
      'the Lyapunov controller spends at most 9.1% of the horizon in violation',
      'Table IV')
check(all(r['in_violation_pct'] >= 91.0 for r in greedy
          if r['budget_fraction'] <= 0.8),
      'greedy is in violation for at least 91% of the horizon up to a 0.8 '
      'budget', 'Table IV')
check(all(next(g['mAP'] for g in greedy
               if g['budget_fraction'] == r['budget_fraction']) >= r['mAP']
          for r in lyap),
      'the guarantee costs accuracy at every budget fraction', 'Table IV')

# Fig. 11(a)
f11a = group(load('fig11a_cumulative_energy'), 'policy')
end = dict((k, v[-1]['cumulative_energy_mWh']) for k, v in f11a.items())
check(end['Greedy (ECORE)'] > end['Budget envelope'],
      'greedy finishes above the 70% envelope', 'Fig. 11(a)')
check(end['Lyapunov controller'] <= end['Budget envelope'] * 1.02,
      'the Lyapunov controller finishes at or below the 70% envelope',
      'Fig. 11(a)')
check(all(all(v[i]['cumulative_energy_mWh']
              <= v[i + 1]['cumulative_energy_mWh'] + 1e-6
              for i in range(len(v) - 1)) for v in f11a.values()),
      'every cumulative-energy curve is non-decreasing', 'Fig. 11(a)')

# Fig. 12
f12a = group(load('fig12a_budget_overshoot'), 'policy')
g = [r['final_overshoot_pct'] for r in f12a['Greedy (ECORE)']]
check(near(g[0], 57.7, 0.15),
      'greedy overshoots by 57.7%% at beta = 0 (computed %.1f%%)' % g[0],
      'Sec. VII / Fig. 12(a)')
check(near(max(g), 61.2, 0.3),
      "greedy's overshoot grows to 61.2%% at the widest beta (computed %.1f%%)"
      % max(g), 'Sec. VII / Fig. 12(a)')
lv = [r['final_overshoot_pct'] for r in f12a['Lyapunov controller']]
check(max(abs(v) for v in lv) <= 5.0,
      'the Lyapunov overshoot stays bounded across all beta '
      '(max |dev| = %.1f%%)' % max(abs(v) for v in lv),
      'Theorem 2 / Fig. 12(a)')
f12b = group(load('fig12b_accuracy_cost'), 'policy')
check(all(a['mean_mAP'] >= b['mean_mAP'] for a, b in
          zip(f12b['Greedy (ECORE)'], f12b['Lyapunov controller'])),
      'greedy keeps its accuracy edge at every staleness level', 'Fig. 12(b)')


# Fig. 13
def grid(name):
    with open(os.path.join(DATA_DIR, name + '.csv'), newline='',
              encoding='utf-8') as fh:
        rdr = csv.reader(fh)
        head = next(rdr)
        rows = [r for r in rdr if r]
    return head, rows, [[float(v) for v in r[1:]] for r in rows]


head_a, rows_a, ga = grid('fig13a_thermal_grid')
flat = [v for row in ga for v in row]
check(near(min(flat), 7.8, 0.05) and near(max(flat), 12.4, 0.05),
      'the thermal saving spans 7.8-12.4%% (computed %.1f-%.1f%%)'
      % (min(flat), max(flat)), 'Sec. VII / Fig. 13(a)')
check(all(near(row[0], 11.9, 0.05) for row in ga),
      'at R_th = 2.5 the saving is 11.9% for every k_thr (nothing throttles)',
      'Sec. VII / Fig. 13(a)')
check(head_a[1:] == ['R_th_2.5', 'R_th_4', 'R_th_5.5', 'R_th_7', 'R_th_8.5'],
      'Fig. 13(a) sweeps R_th over 2.5, 4, 5.5, 7, 8.5', 'Fig. 13(a)')
check([r[0] for r in rows_a] == ['0.01', '0.025', '0.04', '0.055', '0.07'],
      'Fig. 13(a) sweeps k_thr over 0.01, 0.025, 0.04, 0.055, 0.07',
      'Fig. 13(a)')

head_b, rows_b, gb = grid('fig13b_battery_grid')
check([round(row[1], 1) for row in gb] == [3.3, 8.9, 13.5],
      'at nominal capacity the inversion rates are 3.3%, 8.9%, 13.5%',
      'Sec. VII / Fig. 13(b)')
check(near(gb[2][0], 45.7, 0.05),
      'the worst cell (0.5x capacity, a = 0.33) reaches 45.7%', 'Fig. 13(b)')
check(all(row[0] > row[1] > row[2] - 1e-9 for row in gb),
      'inversions fall monotonically as pack capacity grows, at every sag',
      'Sec. VII / Fig. 13(b)')

# regenerated artefacts
STEMS = ['fig07_static_baselines', 'fig08_saving_under_drift',
         'fig09_rank_inversions', 'fig10_reprofiling_cost',
         'fig11_budget_adherence', 'fig12_staleness_robustness',
         'fig13_sensitivity']
missing = [s for s in STEMS
           if not os.path.exists(os.path.join(FIG_DIR, s + '.pdf'))]
if missing:
    check(False, 'figures/*.pdf present for all 7 figures (missing: %s)'
          % missing, 'build')
else:
    small = [s for s in STEMS
             if os.path.getsize(os.path.join(FIG_DIR, s + '.pdf')) < 4000]
    check(not small,
          'all 7 figure PDFs were written and are non-trivial in size', 'build')

passed = sum(1 for ok, _, _ in RESULTS if ok)
width = max(len(w) for _, _, w in RESULTS)
print('')
for ok, what, where in RESULTS:
    if ok and not VERBOSE:
        continue
    print('  %s  %-*s  %s' % ('PASS' if ok else 'FAIL', width, where, what))
print('')
print('  %d/%d checks passed.' % (passed, len(RESULTS)))
if passed != len(RESULTS):
    print('  Some figure or table data no longer agrees with the paper.')
sys.exit(0 if passed == len(RESULTS) else 1)
