# Fig. 7: static profile reproduction, drift disabled.

import numpy as np
import matplotlib.pyplot as plt

from common import (BLUE, FS, GREYBAR, NOTE, TEXTWIDTH_IN, cols, load, save,
                    use_style)

use_style()
rows = load('fig07_static_baselines')

labels = [r['policy'] for r in rows]
is_ec = [r['is_ecore'] for r in rows]
energy, acc, lat = cols(rows, 'energy_mWh', 'mAP', 'latency_ms')

colors = [BLUE if e else GREYBAR for e in is_ec]
y = np.arange(len(labels))[::-1]

fig, axs = plt.subplots(1, 3, figsize=(0.76 * TEXTWIDTH_IN, 1.90))
for ax, vals, ttl, xlab in zip(
        axs, [energy, acc, lat],
        ['(a)  Energy', '(b)  Accuracy', '(c)  Latency'],
        ['Total energy (mWh)', 'Mean mAP', 'Mean latency (ms)']):
    ax.barh(y, vals, height=0.62, color=colors, zorder=3)
    ax.set_title(ttl, loc='left', pad=4)
    ax.set_xlabel(xlab, labelpad=2)
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(-0.7, len(labels) + 0.45)
    ax.tick_params(axis='y', length=0)

axs[0].set_yticks(y)
axs[0].set_yticklabels(labels)
for ax in axs[1:]:
    ax.set_yticks(y)
    ax.set_yticklabels([])

n_static = sum(1 for e in is_ec if not e)
for ax in axs:
    ax.axhline(len(labels) - n_static - 0.5, color='#CBD5E0', lw=0.6,
               ls=(0, (3, 2)), zorder=2)

axs[2].text(0.975, 0.985, 'Drift disabled\nMean ± SD, 10 seeds',
            transform=axs[2].transAxes, ha='right', va='top',
            fontsize=FS - 1.6, color=NOTE, linespacing=1.4,
            bbox=dict(boxstyle='round,pad=0.3', fc='white',
                      ec='#CBD5E0', lw=0.5, alpha=0.9))

fig.subplots_adjust(wspace=0.14)
save(fig, 'fig07_static_baselines')
