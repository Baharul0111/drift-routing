# Arrival process and the sticky Markov object-count stream.

import math
import random


class Workload(object):
    """Poisson arrivals carrying an object-count group that is sticky.

    A frame's object count rarely changes between consecutive frames of the
    same scene, so an i.i.d. group draw would understate how long a routing
    mistake persists. `stickiness` is the probability of staying in the
    current group.
    """

    def __init__(self, rate, groups, seed, stickiness=0.92, dwell_s=None):
        self.rate = float(rate)
        self.groups = list(groups)
        self.rng = random.Random(seed)
        self.stickiness = stickiness
        self.dwell = dwell_s
        self.group = self.rng.choice(self.groups)
        self._t = 0.0
        self._last_switch = 0.0

    def next_arrival(self):
        """-> (t, group). Exponential gap, then the group update."""
        self._t += self.rng.expovariate(self.rate)
        if self.dwell is None:
            if self.rng.random() > self.stickiness:
                self.group = self.rng.choice(self.groups)
        elif self._t - self._last_switch >= self.dwell:
            self._last_switch = self._t
            self.group = self.rng.choice(self.groups)
        return self._t, self.group

    def stream(self, horizon):
        while True:
            t, g = self.next_arrival()
            if t > horizon:
                return
            yield t, g


def replay_stream(path, horizon, rate, seed, groups):
    """COCO-style annotation replay: one object count per line.

    Counts are bucketed into the same groups the profile table uses, and the
    arrival times stay Poisson so the two sources are comparable.
    """
    counts = []
    with open(path, encoding='utf-8') as fh:
        for ln in fh:
            ln = ln.strip()
            if ln and not ln.startswith('#'):
                counts.append(int(float(ln.split(',')[-1])))
    if not counts:
        raise ValueError('no object counts in %s' % path)

    edges = [0, 3, 8, 20]
    rng = random.Random(seed)
    t = 0.0
    i = 0
    while True:
        t += rng.expovariate(rate)
        if t > horizon:
            return
        c = counts[i % len(counts)]
        i += 1
        g = groups[min(len(groups) - 1,
                       sum(1 for e in edges if c > e))]
        yield t, g


def poisson_count(rate, window, rng):
    """Knuth's method, used by the contention model for neighbour arrivals."""
    lam = rate * window
    if lam > 30:
        return int(round(rng.gauss(lam, math.sqrt(lam))))
    ell = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= ell:
            return k
        k += 1
