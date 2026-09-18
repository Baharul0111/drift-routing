# The event loop.
#
# One pass over the arrival stream. Node state advances on a fixed slot so
# the thermal and battery models do not have to be integrated per request,
# and the router is called once per arrival with the believed costs only.

import random

from . import estimators, metrics, models, reprofile, routers, workload

SLOT_S = 1.0


class RunConfig(object):
    def __init__(self, **kw):
        self.arm = kw.get('arm', 'greedy')
        self.estimator = kw.get('estimator', 'oracle')
        self.seed = kw.get('seed', 0)
        self.horizon_s = kw.get('horizon_s', 7200.0)
        self.arrival_rate = kw.get('arrival_rate', 30.0)
        self.window_s = kw.get('window_s', 600.0)
        self.mechanisms = kw.get('mechanisms',
                                 ('thermal', 'contention', 'battery'))
        self.delta_mAP = kw.get('delta_mAP', 5.0)
        self.epsilon = kw.get('epsilon', 0.01)
        self.tau_q = kw.get('tau_q', 0.15)
        self.V = kw.get('V', 1.0)
        self.reserve = kw.get('reserve', 0.02)
        self.beta = kw.get('beta', 0.0)
        self.budget_fraction = kw.get('budget_fraction', None)
        self.budget_mWh = kw.get('budget_mWh', None)
        self.budget_mWh_per_request = kw.get('budget_mWh_per_request', 0.0)
        self.R_th = kw.get('R_th', 5.5)
        self.k_thr = kw.get('k_thr', 0.04)
        self.sag_a = kw.get('sag_a', 0.22)
        self.cap_scale = kw.get('cap_scale', 1.0)
        self.kappa_max = kw.get('kappa_max', 1.25)
        self.pool_size = kw.get('pool_size', 14)
        self.reprofile = kw.get('reprofile', 'never')
        self.probe_cost_mWh = kw.get('probe_cost_mWh', 0.6)
        self.probe_min_gap_s = kw.get('probe_min_gap_s', 30.0)
        self.replay = kw.get('replay', None)
        self.gateway_mWh = kw.get('gateway_mWh', 0.0)

    def as_dict(self):
        return dict((k, v) for k, v in vars(self).items())


class NodeState(object):
    """Per-node runtime state: the three drift models plus a busy estimate."""

    def __init__(self, node, cfg):
        self.node = node
        self.thermal, self.contention, self.battery = models.make_node_models(
            node, cfg.mechanisms, cfg.R_th, cfg.k_thr, cfg.sag_a,
            cfg.cap_scale, cfg.kappa_max)
        self.busy_ms = 0.0
        self.served = 0

    def energy_multiplier(self):
        return (self.thermal.energy_multiplier()
                * self.contention.energy_multiplier()
                * self.battery.energy_multiplier())

    def latency_multiplier(self):
        return (self.thermal.latency_multiplier()
                * self.contention.latency_multiplier()
                * self.battery.latency_multiplier())

    def advance(self, t, dt, rng):
        busy = min(1.0, self.busy_ms / (dt * 1000.0))
        self.thermal.advance(dt, busy)
        self.contention.advance(t, dt, rng)
        self.busy_ms = 0.0


class Fleet(object):
    def __init__(self, nodes, cfg):
        self.nodes = dict((n, NodeState(n, cfg)) for n in nodes)

    def exhausted(self, node):
        return self.nodes[node].battery.exhausted()

    def advance(self, t, dt, rng):
        for s in self.nodes.values():
            s.advance(t, dt, rng)


class Simulation(object):
    def __init__(self, table, cfg):
        self.table = table
        self.cfg = cfg
        self.pool = table.candidate_pool(cfg.pool_size, cfg.delta_mAP)
        self.groups = sorted(self.pool)
        self.nodes = sorted(set(p.node for g in self.pool
                                for p in self.pool[g]))

        s = cfg.seed
        self.rng = random.Random(1000 + s)
        self.est = estimators.make(cfg.estimator, self.groups,
                                   random.Random(2000 + s))
        self.router = routers.make(cfg.arm, self.pool, cfg, 3000 + s)
        self.reprof = reprofile.make(cfg.reprofile, cfg, self.nodes,
                                     random.Random(4000 + s))
        self.fleet = Fleet(self.nodes, cfg)
        self.rec = metrics.Recorder(cfg.horizon_s, cfg.window_s)

        # believed energy per pair: the static profile, optionally perturbed
        # by (1 + beta_p) with |beta_p| <= beta, fixed for the whole run
        pert = random.Random(5000 + s)
        self.believed = {}
        for g in self.groups:
            vals = []
            for p in self.pool[g]:
                b = cfg.beta * (2.0 * pert.random() - 1.0)
                vals.append(p.energy * (1.0 + b))
            self.believed[g] = vals

        # what the router currently believes each node's cost multiplier to
        # be. A probe writes the node's true multiplier here and it stays
        # until the next probe, which is what makes re-profiling worth
        # anything at all: a refresh that lasted one decision could never
        # repay its own energy.
        self.refresh = dict((n, 1.0) for n in self.nodes)

        # a per-request budget for the Lyapunov queue
        if cfg.budget_mWh_per_request <= 0 and cfg.budget_mWh:
            n_exp = cfg.arrival_rate * cfg.horizon_s
            cfg.budget_mWh_per_request = cfg.budget_mWh / n_exp
            # aim a little under the budget: the queue only exerts pressure
            # while it is positive, so a controller that targets the budget
            # exactly settles at a small persistent excess above it
            self.router.budget_per_req = (cfg.budget_mWh_per_request
                                          * (1.0 - cfg.reserve))

    def true_energy(self, pair):
        """Profile energy moved by whatever the node's state currently is."""
        return pair.energy * self.fleet.nodes[pair.node].energy_multiplier()

    def run(self):
        cfg = self.cfg
        if cfg.replay:
            stream = workload.replay_stream(cfg.replay, cfg.horizon_s,
                                            cfg.arrival_rate, 6000 + cfg.seed,
                                            self.groups)
        else:
            wl = workload.Workload(cfg.arrival_rate, self.groups,
                                   6000 + cfg.seed)
            stream = wl.stream(cfg.horizon_s)

        next_slot = SLOT_S
        next_sample = 0.0
        sample_every = max(cfg.horizon_s / 200.0, 1.0)

        for t, true_group in stream:
            while t >= next_slot:
                self.fleet.advance(next_slot, SLOT_S, self.rng)
                next_slot += SLOT_S

            g = self.est.estimate(true_group)
            cand = self.pool[g]

            # a re-profiling probe writes one node's true multiplier into
            # the router's view, where it persists until the next probe
            for node in self.nodes:
                st = self.fleet.nodes[node]
                m = st.energy_multiplier()
                stale = abs(m / self.refresh[node] - 1.0)
                if self.reprof.due(t, node, stale):
                    self.rec.probe_mWh += self.reprof.charge()
                    self.refresh[node] = m

            believed = [e * self.refresh[p.node]
                        for p, e in zip(cand, self.believed[g])]

            pair = self.router.select(g, believed, self.fleet)
            st = self.fleet.nodes[pair.node]

            # the routing decision is judged on the pair alone; the
            # estimator and gateway overheads are common to every option and
            # would otherwise register as an inversion on every request
            e_route = self.true_energy(pair)
            overhead = self.est.cost_mWh + cfg.gateway_mWh
            e_true = e_route + overhead
            lat = pair.latency * st.latency_multiplier()

            feas = self._feasible(true_group)
            best_true = min(self.true_energy(q) for q in feas) \
                if feas else e_true

            st.battery.draw(e_true)
            st.busy_ms += lat
            st.served += 1
            self.router.observe(pair, e_true)
            self.rec.add(t, e_true, pair.mAP, lat, e_route, best_true)

            if t >= next_sample:
                self.rec.sample_cumulative(t)
                next_sample += sample_every

        self.rec.sample_cumulative(cfg.horizon_s)
        return self.summary()

    def _feasible(self, group):
        return routers.feasible_set(self.pool[group], self.cfg, self.fleet)

    def summary(self):
        cfg = self.cfg
        total = self.rec.total_energy()
        out = {
            'arm': cfg.arm,
            'estimator': cfg.estimator,
            'seed': cfg.seed,
            'mechanisms': list(cfg.mechanisms),
            'beta': cfg.beta,
            'energy_mWh': total,
            'energy_Wh': total / 1000.0,
            'mAP': self.rec.mean_mAP(),
            'latency_ms': self.rec.mean_latency(),
            'inversion_rate': self.rec.inversion_rate(),
            'inversion_rate_pct': 100.0 * self.rec.inversion_rate(),
            'late_inversion_rate_pct': self.rec.late_inversion_rate(),
            'probe_mWh': self.rec.probe_mWh,
            'regret_mWh': self.rec.regret_mWh,
            'reprofile': self.reprof.name,
            'windows': self.rec.series(),
            'cumulative': self.rec.cum,
        }
        out['breakeven'] = self.breakeven()
        if cfg.budget_mWh:
            out['budget_mWh'] = cfg.budget_mWh
            out['final_overshoot_pct'] = 100.0 * (total - cfg.budget_mWh) \
                / cfg.budget_mWh
            out['in_violation_pct'] = self._violation_fraction(cfg.budget_mWh)
        return out

    def breakeven(self):
        """Theorem 3, evaluated on this run.

        A probing policy recovers a fraction eta of the inversion penalty
        Pi at an expected cost of at least c*eta*H/(D*pi_star), so it can
        break even only if

            Pi >= c*H/(D*pi_star),

        a condition that does not depend on eta: if it fails, no policy
        breaks even at any detection rate. With the penalty spread evenly,
        pi_star = 1/K and the threshold is c*K*H/D.
        """
        c = self.cfg.probe_cost_mWh
        K = len(self.nodes)
        H = self.cfg.horizon_s
        D = Contention_burst = 60.0
        Pi = self.rec.regret_mWh
        thresh = c * K * H / D
        return {
            'penalty_mWh': Pi,
            'threshold_mWh': thresh,
            'probe_cost_mWh': c,
            'n_nodes': K,
            'burst_len_s': D,
            'can_break_even': Pi >= thresh,
            'margin': (Pi / thresh) if thresh else float('inf'),
        }

    def _violation_fraction(self, budget):
        """Fraction of the horizon spent above the linear budget envelope."""
        if not self.rec.cum:
            return 0.0
        H = self.cfg.horizon_s / 60.0
        over = 0
        for t_min, e in self.rec.cum:
            envelope = budget * (t_min / H) if H else budget
            if e > envelope:
                over += 1
        return 100.0 * over / len(self.rec.cum)
