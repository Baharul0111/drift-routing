# Fig. 8: energy saving relative to HMG while drift is active.

import matplotlib.pyplot as plt

from common import (BLUE, COLWIDTH_IN, FS, GREEN, NOTE, ORANGE, SEED_NOTE,
                    group, inside_legend, load, save, use_style)

use_style()
by = group(load('fig08_saving_under_drift'), 'estimator')

series = [('ECORE (oracle)', BLUE),
          ('ECORE (ED)', ORANGE),
          ('ECORE (OB)', GREEN)]

fig, ax = plt.subplots(figsize=(COLWIDTH_IN, 2.05))
for name, col in series:
    rows = by[name]
    x = [r['elapsed_min'] for r in rows]
    ax.fill_between(x, [r['sd_lo'] for r in rows], [r['sd_hi'] for r in rows],
                    color=col, alpha=0.16, lw=0, zorder=2)
    ax.plot(x, [r['saving_pct'] for r in rows], color=col, lw=1.3,
            marker='o', ms=2.8, label=name, zorder=3)

ax.axhline(0, color='#A0AEC0', lw=0.6, ls=(0, (3, 2)), zorder=1)
ax.set_xlabel('Elapsed time (min)', labelpad=2)
ax.set_ylabel('Energy saving relative to HMG (%)', labelpad=2)
ax.yaxis.grid(True)
ax.set_axisbelow(True)
ax.set_xlim(10, 125)
ax.set_ylim(-7, 30)

inside_legend(ax, 'upper right')
ax.text(0.015, 0.02, SEED_NOTE, transform=ax.transAxes,
        ha='left', va='bottom', fontsize=FS - 1.6, color=NOTE)
save(fig, 'fig08_saving_under_drift')
