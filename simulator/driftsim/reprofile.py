# Re-profiling policies: when to spend energy on a probe that refreshes one
# node's believed cost.
#
# Theorem 3 says a policy breaks even only if the total inversion penalty
# exceeds c*H/(D*pi_star), independently of how good its detection is. For
# contention (D of order a minute) that condition fails, which is what
# Table III measures.


class Never(object):
    name = 'Never'

    def __init__(self, cfg, nodes, rng):
        self.cfg = cfg
        self.nodes = list(nodes)
        self.rng = rng
        self.probe_mWh = 0.0

    def due(self, t, node, staleness):
        return False

    def charge(self):
        self.probe_mWh += self.cfg.probe_cost_mWh
        return self.cfg.probe_cost_mWh


class FixedInterval(Never):
    def __init__(self, cfg, nodes, rng, period_s):
        Never.__init__(self, cfg, nodes, rng)
        self.period = period_s
        self.name = 'Fixed %g s' % period_s
        self.last = dict((n, -1e9) for n in self.nodes)

    def due(self, t, node, staleness):
        if t - self.last[node] >= self.period:
            self.last[node] = t
            return True
        return False


class StalenessTriggered(Never):
    """Probe a node once its believed cost is suspected to be off by more
    than `thresh` in relative terms."""

    def __init__(self, cfg, nodes, rng, thresh):
        Never.__init__(self, cfg, nodes, rng)
        self.thresh = thresh
        self.name = 'Staleness %g' % thresh
        self.last = dict((n, -1e9) for n in self.nodes)

    def due(self, t, node, staleness):
        if staleness < self.thresh:
            return False
        if t - self.last[node] < self.cfg.probe_min_gap_s:
            return False
        self.last[node] = t
        return True


def make(spec, cfg, nodes, rng):
    """spec: 'never', 'fixed:1800', 'staleness:0.03'."""
    if spec in (None, '', 'never'):
        return Never(cfg, nodes, rng)
    kind, _, arg = spec.partition(':')
    if kind == 'fixed':
        return FixedInterval(cfg, nodes, rng, float(arg))
    if kind == 'staleness':
        return StalenessTriggered(cfg, nodes, rng, float(arg))
    raise KeyError('unknown re-profiling policy: %s' % spec)
