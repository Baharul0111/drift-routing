# Fig. 13: sensitivity of both headline results to the drift parameters.
# Both CSVs are grids: column 0 is the row's y value, the other column names
# carry the x values, and rows run bottom to top.

import csv
import os

import numpy as np
import matplotlib.pyplot as plt

from common import DATA_DIR, FS, NOTE, TEXTWIDTH_IN, save, use_style

use_style()


def read_grid(name, xprefix):
    with open(os.path.join(DATA_DIR, name + '.csv'), newline='',
              encoding='utf-8') as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        rows = [r for r in rdr if r]
    xticks = [h[len(xprefix):] for h in header[1:]]
    yticks = [r[0] for r in rows]
    grid = np.array([[float(v) for v in r[1:]] for r in rows])
    return grid, xticks, yticks


def panel(ax, grid, xticks, yticks, xlab, ylab, cblab, note):
    im = ax.imshow(grid, cmap='viridis', aspect='auto', origin='lower')
    ax.set_xticks(range(grid.shape[1]))
    ax.set_xticklabels(xticks)
    ax.set_yticks(range(grid.shape[0]))
    ax.set_yticklabels(yticks)
    ax.set_xlabel(xlab, labelpad=2)
    ax.set_ylabel(ylab, labelpad=2)
    lo, hi = grid.min(), grid.max()
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid[i, j]
            ax.text(j, i, '%.1f' % v, ha='center', va='center',
                    fontsize=FS - 0.6, weight='bold',
                    color=('#1A202C'
                           if (v - lo) / (hi - lo + 1e-9) > 0.62 else 'white'))
    cb = ax.figure.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    cb.set_label(cblab, labelpad=3, fontsize=FS - 0.4)
    cb.ax.tick_params(labelsize=FS - 1.2, width=0.6)
    cb.outline.set_linewidth(0.5)
    ax.grid(False)
    ax.text(0.5, -0.30, note, transform=ax.transAxes, ha='center', va='top',
            fontsize=FS - 2.0, color=NOTE)


ga, xa, ya = read_grid('fig13a_thermal_grid', 'R_th_')
gb, xb, yb = read_grid('fig13b_battery_grid', 'cap_')
xb = [t.replace('x', '×') for t in xb]

fig, axs = plt.subplots(1, 2, figsize=(0.84 * TEXTWIDTH_IN, 2.15))
panel(axs[0], ga, xa, ya,
      'Thermal resistance, $R_\\mathrm{th}$ (°C W$^{-1}$)',
      'Throttle slope, $k_\\mathrm{thr}$ (°C$^{-1}$)',
      'Energy saving vs HMG (%)',
      'Five seeds per cell; 10-seed nominal at the $R_\\mathrm{th}$, '
      '$k_\\mathrm{thr}$ of Table I.')
panel(axs[1], gb, xb, yb,
      'Pack capacity (multiple of nominal)',
      'Efficiency-sag coefficient $a$',
      'Inversion rate, final quarter (%)',
      'Three seeds per cell; nominal $a=0.22$, 1× capacity.')
axs[0].set_title('(a)  Thermal model: headline saving', loc='left', pad=4,
                 fontsize=FS)
axs[1].set_title('(b)  Battery model: late-horizon inversions', loc='left',
                 pad=4, fontsize=FS)
fig.subplots_adjust(wspace=0.62)
save(fig, 'fig13_sensitivity')
