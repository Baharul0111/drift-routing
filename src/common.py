import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(ROOT, 'data')
FIG_DIR = os.path.join(ROOT, 'figures')
TAB_DIR = os.path.join(ROOT, 'tables')

TEXTWIDTH_IN = 7.16
COLWIDTH_IN = 3.44

ORANGE = '#C05621'
BLUE = '#2B6CB0'
GREEN = '#2F855A'
GREY = '#4A5568'
GREYBAR = '#99A6B0'
NOTE = '#6B7C8C'

FS = 7.4

SEED_NOTE = 'Mean ± SD across 10 seeds'

_META = {'Creator': 'matplotlib', 'CreationDate': None}


def use_style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': FS,
        'axes.titlesize': FS + 0.6,
        'axes.labelsize': FS,
        'xtick.labelsize': FS - 0.4,
        'ytick.labelsize': FS - 0.4,
        'legend.fontsize': FS - 0.4,
        'axes.titleweight': 'bold',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.edgecolor': '#B8C2CC',
        'axes.linewidth': 0.7,
        'grid.color': '#E2E8F0',
        'grid.linewidth': 0.6,
        'xtick.color': '#4A5568',
        'ytick.color': '#4A5568',
        'xtick.major.width': 0.7,
        'ytick.major.width': 0.7,
        'figure.facecolor': 'white',
        'savefig.facecolor': 'white',
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.02,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    })


def inside_legend(ax, loc, ncol=1, **kw):
    lg = ax.legend(loc=loc, ncol=ncol, frameon=True, framealpha=0.92,
                   edgecolor='#CBD5E0', fancybox=False, borderpad=0.4,
                   handlelength=1.6, handletextpad=0.5,
                   columnspacing=1.1, labelspacing=0.35, **kw)
    lg.get_frame().set_linewidth(0.5)
    return lg


def save(fig, stem):
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, stem + '.pdf'), dpi=400, metadata=_META)
    fig.savefig(os.path.join(FIG_DIR, stem + '.png'), dpi=400,
                metadata={'Software': None})
    plt.close(fig)
    print('  figures/%s.pdf  figures/%s.png' % (stem, stem))


TEXT_COLS = ('policy', 'estimator', 'platform', 'mechanism', 'fig_label',
             'significant')


def _num(s):
    s = (s or '').strip()
    if s == '':
        return None
    try:
        return float(s)
    except ValueError:
        return s


def load(name):
    path = os.path.join(DATA_DIR, name + '.csv')
    with open(path, newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    return [{k: (v if k in TEXT_COLS else _num(v)) for k, v in r.items()}
            for r in rows]


def group(rows, key):
    out = {}
    for r in rows:
        out.setdefault(r[key], []).append(r)
    return out


def cols(rows, *names):
    return [[r[n] for r in rows] for n in names]
