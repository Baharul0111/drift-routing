# Per-window accounting: energy, accuracy, latency, inversions and regret.

MATERIAL = 0.05   # a rank swap counts only if it costs >5% of the true cost


class Window(object):
    __slots__ = ('t0', 't1', 'n', 'energy', 'mAP', 'latency', 'inversions',
                 'penalty', 'best_energy')

    def __init__(self, t0, t1):
        self.t0 = t0
        self.t1 = t1
        self.n = 0
        self.energy = 0.0
        self.mAP = 0.0
        self.latency = 0.0
        self.inversions = 0
        self.penalty = 0.0
        self.best_energy = 0.0

    def add(self, energy, mAP, latency, chosen_true, best_true):
        self.n += 1
        self.energy += energy
        self.mAP += mAP
        self.latency += latency
        self.best_energy += best_true
        gap = chosen_true - best_true
        if best_true > 0 and gap / best_true > MATERIAL:
            self.inversions += 1
            self.penalty += gap

    def summary(self):
        n = max(self.n, 1)
        return {
            't_min': self.t1 / 60.0,
            'n': self.n,
            'energy_mWh': self.energy,
            'mAP': self.mAP / n,
            'latency_ms': self.latency / n,
            'inversion_rate_pct': 100.0 * self.inversions / n,
            'energy_penalty_mWh': self.penalty,
        }


class Recorder(object):
    """Windowed metrics plus the running totals a run summary reports."""

    def __init__(self, horizon_s, window_s):
        self.window_s = window_s
        self.windows = []
        t = 0.0
        while t < horizon_s - 1e-9:
            self.windows.append(Window(t, min(t + window_s, horizon_s)))
            t += window_s
        self.cum = []          # (t_min, cumulative energy mWh)
        self._running = 0.0
        self.probe_mWh = 0.0
        self.regret_mWh = 0.0
        self.dropped = 0

    def _window(self, t):
        i = min(int(t / self.window_s), len(self.windows) - 1)
        return self.windows[i]

    def add(self, t, energy, mAP, latency, chosen_true, best_true):
        self._window(t).add(energy, mAP, latency, chosen_true, best_true)
        self._running += energy
        self.regret_mWh += max(0.0, chosen_true - best_true)

    def sample_cumulative(self, t):
        self.cum.append((t / 60.0, self._running))

    def total_energy(self):
        return sum(w.energy for w in self.windows)

    def mean_mAP(self):
        n = sum(w.n for w in self.windows)
        if not n:
            return 0.0
        return sum(w.mAP for w in self.windows) / n

    def mean_latency(self):
        n = sum(w.n for w in self.windows)
        if not n:
            return 0.0
        return sum(w.latency for w in self.windows) / n

    def inversion_rate(self):
        n = sum(w.n for w in self.windows)
        if not n:
            return 0.0
        return float(sum(w.inversions for w in self.windows)) / n

    def late_inversion_rate(self):
        """Final quarter of the horizon, which is what Fig. 13(b) reports."""
        k = max(1, len(self.windows) // 4)
        tail = self.windows[-k:]
        n = sum(w.n for w in tail)
        if not n:
            return 0.0
        return 100.0 * sum(w.inversions for w in tail) / n

    def series(self):
        return [w.summary() for w in self.windows]
