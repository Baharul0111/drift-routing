# Generates profiles/example_profile_table.csv.
#
# THE OUTPUT IS SYNTHETIC. It exists so the simulator can be run end to end
# by anyone who clones the repository, and so the code paths are exercised by
# `run.py --smoke`. It is not measured data and does not reproduce the
# numbers in ../../data/. Replace it with profile_table.csv, the measured
# table, to reproduce the paper.

import csv
import os
import random

MODELS = [
    # name, relative compute, mAP at the reference group, int8-friendly
    ('nanodet',            0.35, 21.6, True),
    ('yolox_tiny',         0.55, 24.9, True),
    ('yolov8n',            0.70, 27.1, True),
    ('ssd_mobilenet',      0.75, 22.4, True),
    ('efficientdet_d0',    1.10, 30.2, True),
    ('yolov8s',            1.60, 32.4, True),
    ('efficientdet_d2',    2.40, 34.0, True),
    ('yolov8m',            3.10, 35.8, True),
    ('retinanet_r50',      4.60, 36.4, True),
    ('ssd_vgg',            5.10, 29.6, False),
    ('yolov8l',            6.20, 38.1, True),
    ('faster_rcnn_r50',    8.40, 39.2, False),
]

NODES = [
    # name, energy per unit compute (mWh), latency per unit (ms),
    # energy speed-up, latency speed-up, accelerator is int8 only
    #
    # The NPU nodes are faster than their energy advantage alone suggests:
    # the accelerator finishes sooner while the host board keeps drawing, so
    # the latency speed-up exceeds the energy speed-up. That is what stops
    # the lowest-energy and lowest-latency baselines collapsing onto the
    # same pair.
    ('orin_nano',    0.0865,  7.0, 2.55, 2.55, False),
    ('pi5_aihat_a',  0.1365, 10.5, 3.30, 5.20, True),
    ('pi5_aihat_b',  0.1390, 10.7, 3.30, 5.20, True),
    ('pi5_coral_a',  0.1515, 14.0, 2.55, 4.10, True),
    ('pi5_coral_b',  0.1490, 13.8, 2.55, 4.10, True),
    ('pi4_coral',    0.1645, 19.5, 2.40, 3.60, True),
]

# object-count groups and how much work each one implies
GROUPS = [(0, 0.82), (1, 1.00), (2, 1.26), (3, 1.58)]

rng = random.Random(20260918)
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, 'example_profile_table.csv')

rows = []
for mname, flops, base_map, int8 in MODELS:
    for nname, e_unit, l_unit, e_accel, l_accel, int8_only in NODES:
        usable = int8 or not int8_only
        e_speed = e_accel if usable else 1.0
        l_speed = l_accel if usable else 1.0
        for g, scale in GROUPS:
            jitter = 1.0 + 0.04 * (rng.random() - 0.5)
            energy = flops * scale * e_unit / e_speed * jitter
            latency = flops * scale * l_unit / l_speed * jitter
            # accuracy falls slightly on crowded frames, more so for small
            # models, and int8 quantisation costs a little on every node
            crowd = 1.0 - 0.022 * g * (1.0 + 0.8 / (flops + 1.0))
            quant = 0.985 if (int8 and int8_only and e_speed > 1) else 1.0
            mAP = base_map * crowd * quant
            rows.append([mname, nname, g, round(energy, 5),
                         round(mAP, 3), round(latency, 3)])

with open(out, 'w', newline='', encoding='utf-8') as fh:
    fh.write('# SYNTHETIC example table. Not measured data. See README.md.\n')
    w = csv.writer(fh)
    w.writerow(['model', 'node', 'group', 'energy_mWh', 'mAP', 'latency_ms'])
    w.writerows(rows)

pairs = len(MODELS) * len(NODES)
print('wrote %s: %d pairs x %d groups = %d rows'
      % (os.path.basename(out), pairs, len(GROUPS), len(rows)))
