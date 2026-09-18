# Emit Tables I-IV as LaTeX fragments. Needs booktabs in the preamble.
# Tables I and II fit a column; III and IV use table* and span both.

import os

from common import TAB_DIR, group, load

os.makedirs(TAB_DIR, exist_ok=True)


def write(stem, body):
    with open(os.path.join(TAB_DIR, stem + '.tex'), 'w', encoding='utf-8') as fh:
        fh.write(body.rstrip() + '\n')
    print('  tables/%s.tex' % stem)


rows = load('table1_platform_thermal')
body = []
for r in rows:
    u = r['u_thr_pct']
    us = 'never' if u == 'never' else '%.1f\\%%' % float(u)
    ms = '--' if r['m_max'] in (None, '') else '%.2f' % float(r['m_max'])
    body.append('    %s & %s & %s \\\\' % (r['platform'], us, ms))
write('table1_platform_thermal', r"""
\begin{table}[t]
  \centering
  \caption{Sustained-load threshold and worst-case slowdown by platform.
    $u_\mathrm{thr}$ is the duty cycle above which the platform throttles;
    $m_\mathrm{max}$ is the resulting worst-case latency multiplier.}
  \label{tab:platform-thermal}
  \small
  \begin{tabular}{lrr}
    \toprule
    Platform & $u_\mathrm{thr}$ & $m_\mathrm{max}$ \\
    \midrule
""" + '\n'.join(body) + r"""
    \bottomrule
  \end{tabular}
\end{table}
""")


rows = load('table2_mechanism_ablation')
body = ['    %s & %.1f & %.4f & %.2f \\\\'
        % (r['mechanism'], r['energy_Wh'], r['inversion_rate'], r['mAP'])
        for r in rows]
write('table2_mechanism_ablation', r"""
\begin{table}[t]
  \centering
  \caption{Mechanism ablation. Each drift mechanism is enabled alone, then
    all three together, under an otherwise identical workload.}
  \label{tab:mechanism-ablation}
  \footnotesize
  \setlength{\tabcolsep}{4pt}
  \begin{tabular}{lrrr}
    \toprule
    Active mechanism & Energy (Wh) & Inversion rate & mAP \\
    \midrule
""" + '\n'.join(body) + r"""
    \bottomrule
  \end{tabular}
\end{table}
""")


rows = load('table3_reprofiling')
body = []
for r in rows:
    if r['delta_regret_mWh'] is None:
        d, ci = '--', '--'
    else:
        star = '$^{*}$' if r['significant'] else ''
        d = '%+.1f%s' % (r['delta_regret_mWh'], star)
        ci = '[%.1f, %.1f]' % (r['ci_lo'], r['ci_hi'])
    body.append('    %s & %.1f & %.1f & %s & %s \\\\'
                % (r['policy'], r['probe_mWh'], r['regret_mWh'], d, ci))
write('table3_reprofiling', r"""
\begin{table*}[t]
  \centering
  \caption{Re-profiling policies. $\Delta$regret is measured against the
    \emph{Never} row; the interval is the paired 95\% CI. $^{*}$ marks a
    difference that survives the Holm correction.}
  \label{tab:reprofiling}
  \small
  \begin{tabular}{lrrrr}
    \toprule
    Policy & Probe (mWh) & Regret (mWh) & $\Delta$regret & 95\% CI \\
    \midrule
""" + '\n'.join(body) + r"""
    \bottomrule
  \end{tabular}
\end{table*}
""")


rows = load('table4_budget_adherence')
body = []
for frac, grp in group(rows, 'budget_fraction').items():
    for i, r in enumerate(grp):
        head = '%.1f' % frac if i == 0 else ''
        body.append('    %s & %s & %.1f & %+.1f\\%% & %.1f\\%% & %.2f \\\\'
                    % (head, r['policy'], r['energy_Wh'], r['overshoot_pct'],
                       r['in_violation_pct'], r['mAP']))
    body.append(r'    \addlinespace[2pt]')
body.pop()
write('table4_budget_adherence', r"""
\begin{table*}[t]
  \centering
  \caption{Budget adherence across budget fractions. \emph{Overshoot} is the
    final deviation from the budget; \emph{in violation} is the fraction of
    the horizon spent above the envelope.}
  \label{tab:budget-adherence}
  \small
  \begin{tabular}{llrrrr}
    \toprule
    Budget & Policy & Energy (Wh) & Overshoot & In violation & Mean mAP \\
    \midrule
""" + '\n'.join(body) + r"""
    \bottomrule
  \end{tabular}
\end{table*}
""")
