# Rebuild every figure and table, then verify.

import os
import subprocess
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = [
    'fig07_static_baselines.py',
    'fig08_saving_under_drift.py',
    'fig09_rank_inversions.py',
    'fig10_reprofiling_cost.py',
    'fig11_budget_adherence.py',
    'fig12_staleness_robustness.py',
    'fig13_sensitivity.py',
    'make_tables.py',
]

failed = []
for s in SCRIPTS:
    print('[%s]' % s)
    if subprocess.run([sys.executable, os.path.join(SRC, s)], cwd=SRC).returncode:
        failed.append(s)

if failed:
    print('\nfailed: %s' % ', '.join(failed))
    sys.exit(1)

print('\n[verify.py]')
sys.exit(subprocess.run([sys.executable, os.path.join(SRC, 'verify.py')],
                        cwd=SRC).returncode)
