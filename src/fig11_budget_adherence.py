# Fig. 11: budget adherence of greedy against the Lyapunov controller.

import matplotlib.pyplot as plt

from common import (BLUE, FS, GREY, NOTE, ORANGE, TEXTWIDTH_IN, group, load,
                    save, use_style)

use_style()
fig, axs = plt.subplots(1, 2, figsize=(0.76 * TEXTWIDTH_IN, 2.15))

a = group(load('fig11a_cumulative_energy'), 'policy')
for name, col, ls in [('Greedy (ECORE)', ORANGE, '-'),
                      ('Lyapunov controller', BLUE, '-'),
                      ('Budget envelope', GREY, (0, (4, 2)))]:
    if name not in a:
        continue
    rows = a[name]
    axs[0].plot([r['elapsed_min'] for r in rows],
                [r['cumulative_energy_mWh'] for r in rows],
                color=col, lw=1.2, ls=ls, label=name, zorder=3)
axs[0].set_title('(a)  Cumulative energy at 70% budget', loc='left', pad=4,
                 fontsize=FS)
axs[0].set_xlabel('Elapsed time (min)', labelpad=2)
axs[0].set_ylabel('Cumulative energy (mWh)', labelpad=2)
axs[0].set_xticks([0, 20, 40, 60, 80, 100, 120])

b = group(load('fig11b_budget_deviation'), 'policy')
for name, col, mk in [('Greedy (ECORE)', ORANGE, 's'),
                      ('Lyapunov controller', BLUE, 'o')]:
    rows = b[name]
    axs[1].plot([r['budget_fraction'] for r in rows],
                [r['final_deviation_pct'] for r in rows],
                color=col, lw=1.2, marker=mk, ms=3.0, label=name, zorder=3)
axs[1].axhline(0, color=GREY, lw=0.9, ls=(0, (4, 2)), zorder=2,
               label='Budget envelope')
axs[1].set_title('(b)  Final budget deviation', loc='left', pad=4, fontsize=FS)
axs[1].set_xlabel('Budget fraction of HMG energy', labelpad=2)
axs[1].set_ylabel('Final budget deviation (%)', labelpad=2)
axs[1].set_ylim(-18, 150)

for ax in axs:
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)

handles, labels = axs[1].get_legend_handles_labels()
seen = {}
for h, l in zip(handles, labels):
    seen.setdefault(l, h)
axs[1].legend(seen.values(), seen.keys(), loc='upper right', frameon=True,
              framealpha=0.92, edgecolor='#CBD5E0', fancybox=False,
              borderpad=0.4, handlelength=1.8, handletextpad=0.5,
              labelspacing=0.35,
              fontsize=FS - 0.6).get_frame().set_linewidth(0.5)

axs[1].text(0.985, 0.02, 'Panel (b): mean ± SD across 10 seeds',
            transform=axs[1].transAxes, ha='right', va='bottom',
            fontsize=FS - 1.6, color=NOTE)
fig.subplots_adjust(wspace=0.33)
save(fig, 'fig11_budget_adherence')
