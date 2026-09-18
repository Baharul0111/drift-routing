# Fig. 10: probe energy against regret recovered. Same source as Table III:
#   recovered = -delta_regret, net = recovered - probe.

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms

from common import (BLUE, COLWIDTH_IN, FS, GREEN, NOTE, ORANGE,
                    inside_legend, load, save, use_style)

use_style()

rows = [r for r in load('table3_reprofiling') if r['policy'] != 'Never']
rows.sort(key=lambda r: r['probe_mWh'])

policy = [r['fig_label'] for r in rows]
probe = [r['probe_mWh'] for r in rows]
recovered = [-r['delta_regret_mWh'] for r in rows]
ci_half = [(r['ci_hi'] - r['ci_lo']) / 2.0 for r in rows]
net = [r - p for r, p in zip(recovered, probe)]

x = np.arange(len(policy))
w = 0.38

fig, ax = plt.subplots(figsize=(COLWIDTH_IN, 2.25))
ax.bar(x - w / 2, probe, w, color=ORANGE, label='Probe energy spent', zorder=3)
ax.bar(x + w / 2, recovered, w, color=BLUE,
       label='Regret recovered vs never', zorder=3)
ax.errorbar(x + w / 2, recovered, yerr=ci_half, fmt='none',
            ecolor='#4A5568', elinewidth=0.7, capsize=1.6, zorder=4)

ax.set_yscale('symlog', linthresh=1)
ax.axhline(0, color='#718096', lw=0.7, zorder=2)
ax.set_ylabel('mWh (symmetric log scale)', labelpad=2)
ax.set_xticks(x)
ax.set_xticklabels(policy, rotation=32, ha='right')
ax.yaxis.grid(True)
ax.set_axisbelow(True)
ax.set_ylim(-4000, 30000)

# net labels on two rows so neighbours do not collide
tr = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
for xi, n in zip(x, net):
    lab = 'net %s%d' % ('+' if n > 0 else '-', int(abs(n) + 0.5))
    ax.text(xi, 0.97 if xi % 2 == 0 else 0.885, lab, transform=tr,
            ha='center', va='top', fontsize=FS - 2.4,
            color=(GREEN if n > 0 else ORANGE), weight='bold')

inside_legend(ax, 'lower left')
ax.text(0.5, -0.34,
        'Mean ± SD across 10 seeds.  A policy pays for itself\n'
        'only where blue exceeds orange.',
        transform=ax.transAxes, ha='center', va='top',
        fontsize=FS - 2.4, color=NOTE, linespacing=1.3)
save(fig, 'fig10_reprofiling_cost')
