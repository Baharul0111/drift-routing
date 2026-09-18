# Routing policies. Every policy sees the same believed profile; they differ
# in what they do with it, and in whether anything they compute depends on
# realised energy.

import random


def live_set(cand, cfg, state):
    """The tau_q latency constraint and liveness, with no accuracy rule.

    Every arm sits on this same feasibility layer, so a comparison between
    them is never a comparison of who was allowed to use a dead node.
    """
    out = list(cand)
    if cfg.tau_q:
        lim = cfg.tau_q * 1000.0
        keep = [p for p in out if p.latency <= lim]
        out = keep or out
    if state is not None:
        alive = [p for p in out if not state.exhausted(p.node)]
        out = alive or out
    return out


def feasible_set(cand, cfg, state):
    """delta-mAP feasibility, the tau_q latency constraint, and liveness.

    Options are dropped in that order, and the last non-empty set wins: a
    fleet with no live feasible node still has to route something.
    """
    out = live_set(cand, cfg, state)
    best = max(p.mAP for p in out)
    return [p for p in out if p.mAP >= best - cfg.delta_mAP] or out


class Router(object):
    name = 'base'
    uses_realised_energy = False

    def __init__(self, pool, cfg, rng):
        self.pool = pool          # {group: [Pair, ...]}
        self.cfg = cfg
        self.rng = rng

    def select(self, group, believed, state):
        """-> Pair. `believed` is the believed energy of each pair in the
        group's pool, `state` carries per-node runtime state."""
        raise NotImplementedError

    def observe(self, pair, realised_mWh):
        pass


class RoundRobin(Router):
    name = 'round_robin'

    def __init__(self, pool, cfg, rng):
        Router.__init__(self, pool, cfg, rng)
        self.i = 0

    def select(self, group, believed, state):
        cand = live_set(self.pool[group], self.cfg, state)
        p = cand[self.i % len(cand)]
        self.i += 1
        return p


class Random(Router):
    name = 'random'

    def select(self, group, believed, state):
        return self.rng.choice(live_set(self.pool[group], self.cfg, state))


class LowestEnergy(Router):
    name = 'LE'

    def select(self, group, believed, state):
        cand = live_set(self.pool[group], self.cfg, state)
        return min(cand, key=lambda p: p.energy)


class LowestLatency(Router):
    name = 'LI'

    def select(self, group, believed, state):
        cand = live_set(self.pool[group], self.cfg, state)
        return min(cand, key=lambda p: p.latency)


class HighestMAP(Router):
    name = 'HM'

    def select(self, group, believed, state):
        cand = live_set(self.pool[group], self.cfg, state)
        return max(cand, key=lambda p: p.mAP)


class HighestMAPGreedy(Router):
    """Highest accuracy, spread over the nodes that can serve it.

    This is the reference the energy saving in Fig. 8 is measured against.
    Each node in turn contributes its cheapest option within delta_mAP of the
    fleet-wide best, so accuracy stays at the ceiling while the load spreads.
    Spreading is what keeps any single pack from draining early, and it is
    why HMG degrades less over the horizon than greedy does.
    """
    name = 'HMG'

    def __init__(self, pool, cfg, rng):
        Router.__init__(self, pool, cfg, rng)
        self.i = 0

    def select(self, group, believed, state):
        feasible = feasible_set(self.pool[group], self.cfg, state)
        nodes = sorted(set(p.node for p in feasible))
        node = nodes[self.i % len(nodes)]
        self.i += 1
        here = [p for p in feasible if p.node == node]
        return min(here, key=lambda p: p.energy)


class DeltaMapGreedy(Router):
    """ECORE's policy: cheapest believed option within delta_mAP of the best.

    Nothing it computes is a function of realised energy, which is the
    property Theorem 2 turns on: it has no budget guarantee at any staleness,
    including zero.
    """
    name = 'greedy'

    def select(self, group, believed, state):
        feasible = feasible_set(self.pool[group], self.cfg, state)
        return min(feasible, key=lambda p: believed[p.idx])


class Lyapunov(Router):
    """Drift-plus-penalty controller, Eq. (4) of the paper.

        a = argmin_i { Q_i * e_hat_i - V * mAP_i }

    The queue Q is updated from the *realised* energy, not the believed one.
    That single asymmetry is what makes the budget guarantee hold uniformly
    in the sign pattern of the profile error.
    """
    name = 'lyapunov'
    uses_realised_energy = True

    def __init__(self, pool, cfg, rng):
        Router.__init__(self, pool, cfg, rng)
        self.Q = 0.0
        self.budget_per_req = cfg.budget_mWh_per_request

    def select(self, group, believed, state):
        # the accuracy floor is NOT applied here: trading accuracy away is
        # exactly how the controller keeps a budget that greedy blows past,
        # and V is the price it puts on that trade
        cand = live_set(self.pool[group], self.cfg, state)
        V = self.cfg.V
        return min(cand, key=lambda p: self.Q * believed[p.idx] - V * p.mAP)

    def observe(self, pair, realised_mWh):
        self.Q = max(0.0, self.Q + realised_mWh - self.budget_per_req)


ROUTERS = {
    'round_robin': RoundRobin,
    'random': Random,
    'LE': LowestEnergy,
    'LI': LowestLatency,
    'HM': HighestMAP,
    'HMG': HighestMAPGreedy,
    'greedy': DeltaMapGreedy,
    'lyapunov': Lyapunov,
}


def make(name, pool, cfg, seed):
    if name not in ROUTERS:
        raise KeyError('unknown router: %s (have %s)'
                       % (name, ', '.join(sorted(ROUTERS))))
    return ROUTERS[name](pool, cfg, random.Random(seed))
