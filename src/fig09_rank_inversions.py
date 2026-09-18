# Fig. 9: material rank inversions and what they cost, over two hours.

import matplotlib.pyplot as plt

from common import (BLUE, FS, GREEN, NOTE, ORANGE, SEED_NOTE, TEXTWIDTH_IN,
                    group, inside_legend, load, save, use_style)

use_style()

panels = [
    ('fig09a_inversion_rate', 'inversion_rate_pct',
     '(a)  Material inversion rate', 'Inversion rate (%)'),
    ('fig09b_energy_penalty', 'energy_penalty_mWh',
     '(b)  Energy penalty', 'Energy penalty per window (mWh)'),
]
series = [('ECORE (oracle)', BLUE),
          ('ECORE (ED)', ORANGE),
          ('ECORE (OB)', GREEN)]

fig, axs = plt.subplots(1, 2, figsize=(0.76 * TEXTWIDTH_IN, 2.15))
for ax, (src, ycol, ttl, ylab) in zip(axs, panels):
    by = group(load(src), 'estimator')
    for name, col in series:
        rows = by[name]
        x = [r['elapsed_min'] for r in rows]
        ax.fill_between(x, [r['sd_lo'] for r in rows],
                        [r['sd_hi'] for r in rows],
                        color=col, alpha=0.16, lw=0, zorder=2)
        ax.plot(x, [r[ycol] for r in rows], color=col, lw=1.3,
                marker='o', ms=2.8, label=name, zorder=3)
    ax.set_title(ttl, loc='left', pad=4)
    ax.set_xlabel('Elapsed time (min)', labelpad=2)
    ax.set_ylabel(ylab, labelpad=2)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlim(10, 125)
    ax.set_ylim(bottom=0)
    inside_legend(ax, 'upper left')

axs[1].text(0.985, 0.02, SEED_NOTE, transform=axs[1].transAxes,
            ha='right', va='bottom', fontsize=FS - 1.6, color=NOTE)
fig.subplots_adjust(wspace=0.28)
save(fig, 'fig09_rank_inversions')
