# Fig. 12: budget adherence under stale profiles (test of Theorem 2).

import matplotlib.pyplot as plt

from common import (BLUE, FS, NOTE, ORANGE, TEXTWIDTH_IN, group,
                    inside_legend, load, save, use_style)

use_style()

panels = [
    ('fig12a_budget_overshoot', 'final_overshoot_pct',
     '(a)', 'Final budget overshoot (%)', 'center right'),
    ('fig12b_accuracy_cost', 'mean_mAP',
     '(b)', 'Mean mAP', 'center'),
]
series = [('Greedy (ECORE)', ORANGE), ('Lyapunov controller', BLUE)]

fig, axs = plt.subplots(1, 2, figsize=(0.76 * TEXTWIDTH_IN, 2.05))
for ax, (src, ycol, ttl, ylab, loc) in zip(axs, panels):
    by = group(load(src), 'policy')
    for name, col in series:
        rows = by[name]
        x = [r['beta_pct'] for r in rows]
        ax.fill_between(x, [r['sd_lo'] for r in rows],
                        [r['sd_hi'] for r in rows],
                        color=col, alpha=0.16, lw=0, zorder=2)
        ax.plot(x, [r[ycol] for r in rows], color=col, lw=1.3,
                marker='o', ms=2.8, label=name, zorder=3)
    ax.set_title(ttl, loc='left', pad=4)
    ax.set_xlabel('Profile staleness bound β (%)', labelpad=2)
    ax.set_ylabel(ylab, labelpad=2)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlim(-2, 52)
    inside_legend(ax, loc)

axs[0].axhline(0, color='#A0AEC0', lw=0.6, ls=(0, (3, 2)), zorder=1)
axs[0].set_ylim(-4, 72)
fig.text(0.5, -0.06,
         'Mean ± SD across 10 seeds.  Believed energies perturbed by '
         '(1+β$_p$), |β$_p$| ≤ β',
         ha='center', va='top', fontsize=FS - 2.0, color=NOTE)
fig.subplots_adjust(wspace=0.26)
save(fig, 'fig12_staleness_robustness')
