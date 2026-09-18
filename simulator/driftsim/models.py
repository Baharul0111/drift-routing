# The three drift mechanisms. Each one moves the true per-request cost while
# the profile the router consults stays where it was.

import math


class Thermal(object):
    """Duty-cycle throttling with an RC junction-temperature model.

    Sustained load raises die temperature by R_th per watt; above the
    platform's threshold duty the clock falls, latency grows at k_thr per
    degree and saturates at m_max.

    Throttling stretches a request in time and, at a roughly flat idle
    draw, stretches its energy with it. Both multipliers are therefore m,
    and m is capped at the platform's measured m_max. Corollary 1 is the
    observation that m_max is smaller than the 1.64x cross-device gap in the
    profile, so throttling on its own can never reorder the greedy choice.
    """

    def __init__(self, u_thr, m_max, R_th=5.5, k_thr=0.04, tau_s=90.0,
                 ambient_c=25.0, p_active_w=7.0):
        self.u_thr = u_thr
        self.m_max = m_max
        self.R_th = R_th
        self.k_thr = k_thr
        self.tau = tau_s
        self.ambient = ambient_c
        self.p_active = p_active_w
        self.temp = ambient_c
        self.duty = 0.0

    def advance(self, dt, busy_fraction):
        # exponential smoothing of duty, then a first-order thermal response
        alpha = 1.0 - math.exp(-dt / max(self.tau, 1e-6))
        self.duty += alpha * (busy_fraction - self.duty)
        target = self.ambient + self.R_th * self.p_active * self.duty
        self.temp += alpha * (target - self.temp)

    def latency_multiplier(self):
        if self.duty <= self.u_thr:
            return 1.0
        over = self.temp - (self.ambient + self.R_th * self.p_active
                            * self.u_thr)
        if over <= 0:
            return 1.0
        return min(self.m_max, 1.0 + self.k_thr * over)

    def energy_multiplier(self):
        return self.latency_multiplier()


class Contention(object):
    """Cost inflation from a co-resident job on the same node.

    Bursts are short (tens of seconds) and independent across nodes, which is
    what makes them expensive to detect by probing: Theorem 3's break-even
    condition fails because D is small.
    """

    def __init__(self, kappa_max=1.25, burst_rate_per_h=14.0,
                 burst_len_s=45.0):
        self.kappa_max = kappa_max
        self.rate = burst_rate_per_h / 3600.0
        self.burst_len = burst_len_s
        self.until = -1.0
        self.kappa = 1.0

    def advance(self, t, dt, rng):
        if t < self.until:
            return
        self.kappa = 1.0
        if rng.random() < self.rate * dt:
            self.until = t + self.burst_len * (0.5 + rng.random())
            self.kappa = 1.0 + (self.kappa_max - 1.0) * (0.55 + 0.45
                                                         * rng.random())

    def energy_multiplier(self):
        return self.kappa

    def latency_multiplier(self):
        return self.kappa


class Battery(object):
    """Pack depletion and the converter efficiency that sags with it.

    Device-side energy is what the node spends; the pack pays that divided by
    the converter efficiency, which falls as the pack empties. The sag is
    slow and monotone, which is why Theorem 3 admits a profitable probing
    policy here and not for contention.
    """

    def __init__(self, capacity_mWh, sag_a=0.22, eta0=1.0, eta_floor=0.70):
        self.capacity = float(capacity_mWh)
        self.drawn = 0.0
        self.sag_a = sag_a
        self.eta0 = eta0
        self.eta_floor = eta_floor

    def soc(self):
        if self.capacity <= 0:
            return 1.0
        return max(0.0, 1.0 - self.drawn / self.capacity)

    def efficiency(self):
        return max(self.eta_floor, self.eta0 - self.sag_a * (1.0 - self.soc()))

    def energy_multiplier(self):
        return 1.0 / self.efficiency()

    def latency_multiplier(self):
        return 1.0

    def draw(self, mWh_device):
        self.drawn += mWh_device / self.efficiency()

    def exhausted(self):
        return self.capacity > 0 and self.drawn >= self.capacity


PLATFORMS = {
    # name: (u_thr, m_max, idle power W, pack mWh)
    'orin_nano':   (0.890, 1.37, 5.1, 22000.0),
    'pi5_aihat':   (0.545, 1.50, 3.4, 22000.0),
    'pi5_coral':   (0.582, 1.50, 3.1, 22000.0),
    'pi5':         (0.645, 1.67, 3.0, 22000.0),
    'pi4_coral':   (0.693, 1.54, 2.8, 22000.0),
    'pi3':         (None,  None, 1.9, 22000.0),
    'jetson_nano': (None,  None, 2.6, 22000.0),
}


def platform_of(node):
    """Fleet node names carry an instance suffix: pi5_aihat_a -> pi5_aihat."""
    if node in PLATFORMS:
        return node
    base = node.rsplit('_', 1)[0]
    return base if base in PLATFORMS else 'pi5'


def make_node_models(node, mechanisms, R_th, k_thr, sag_a, cap_scale,
                     kappa_max):
    u_thr, m_max, _idle, pack = PLATFORMS[platform_of(node)]
    if u_thr is None or 'thermal' not in mechanisms:
        thermal = Thermal(1e9, 1.0, R_th, k_thr)
    else:
        thermal = Thermal(u_thr, m_max, R_th, k_thr)
    cont = Contention(kappa_max if 'contention' in mechanisms else 1.0)
    batt = Battery(pack * cap_scale,
                   sag_a if 'battery' in mechanisms else 0.0)
    return thermal, cont, batt
