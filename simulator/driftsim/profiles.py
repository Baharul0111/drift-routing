# The model-by-node profile table and the Pareto subset used as the
# candidate pool.

import csv
import os


class Pair(object):
    """One (model, node) pair at one object-count group."""

    __slots__ = ('model', 'node', 'group', 'energy', 'mAP', 'latency', 'idx')

    def __init__(self, model, node, group, energy, mAP, latency):
        self.model = model
        self.node = node
        self.group = group
        self.energy = energy      # mWh per request, at the reference state
        self.mAP = mAP
        self.latency = latency    # ms
        self.idx = -1

    def key(self):
        return (self.model, self.node)

    def __repr__(self):
        return '%s|%s@g%d' % (self.model, self.node, self.group)


def _pareto(pairs):
    """Keep pairs not dominated on (energy low, mAP high).

    Latency is a constraint (tau_q), not a third objective, so it does not
    enter here.
    """
    keep = []
    for a in pairs:
        dominated = False
        for b in pairs:
            if b is a:
                continue
            if (b.energy <= a.energy and b.mAP >= a.mAP
                    and (b.energy < a.energy or b.mAP > a.mAP)):
                dominated = True
                break
        if not dominated:
            keep.append(a)
    return keep


class ProfileTable(object):
    """Believed per-request cost of every pair, by object-count group.

    The table is static: the router consults it for the whole run while the
    true cost moves underneath it. That gap is the subject of the paper.
    """

    def __init__(self, rows):
        self.rows = rows
        self.groups = sorted(set(r.group for r in rows))
        self.by_group = {}
        for g in self.groups:
            self.by_group[g] = [r for r in rows if r.group == g]
        self.nodes = sorted(set(r.node for r in rows))
        self.models = sorted(set(r.model for r in rows))

    @classmethod
    def load(cls, path):
        rows = []
        with open(path, newline='', encoding='utf-8') as fh:
            lines = [ln for ln in fh if not ln.lstrip().startswith('#')]
        for r in csv.DictReader(lines):
            rows.append(Pair(r['model'], r['node'], int(r['group']),
                             float(r['energy_mWh']), float(r['mAP']),
                             float(r['latency_ms'])))
        if not rows:
            raise ValueError('empty profile table: %s' % path)
        return cls(rows)

    def n_pairs(self):
        return len(set(r.key() for r in self.rows))

    def candidate_pool(self, size=None, delta_mAP=5.0):
        """The candidate pool: each node's own efficient frontier.

        A global Pareto filter would keep only the node that happens to be
        cheapest for each model, leaving nothing to route between. The pool
        a router needs is the frontier *within* each node, unioned across the
        fleet, so every node offers an efficient accuracy/energy option and a
        cross-device comparison is possible at all. Trimming to `size` takes
        from the nodes in turn, so no node is squeezed out.
        """
        ref = self.groups[len(self.groups) // 2]

        def cost(key):
            vals = [r.energy for r in self.by_group[ref] if r.key() == key]
            return sum(vals) / len(vals) if vals else 1e9

        def acc(key):
            vals = [r.mAP for r in self.by_group[ref] if r.key() == key]
            return sum(vals) / len(vals) if vals else 0.0

        frontier = {}
        for node in self.nodes:
            keys = []
            for g in self.groups:
                rows = [r for r in self.by_group[g] if r.node == node]
                for p in _pareto(rows):
                    if p.key() not in keys:
                        keys.append(p.key())
            frontier[node] = keys

        # From each node's frontier, keep the options a router would actually
        # consider: the cheapest ones inside that node's own delta_mAP band,
        # then the cheapest ones overall. Taking the top of the frontier by
        # accuracy instead would hand every node its single most expensive
        # option, which is not a candidate any policy would pick.
        if size is not None:
            per = max(2, int(round(float(size) / len(self.nodes))))
            for node in self.nodes:
                fr = frontier[node]
                if len(fr) <= per:
                    continue
                best = max(acc(k) for k in fr)
                band = sorted([k for k in fr if acc(k) >= best - delta_mAP],
                              key=cost)
                n_band = max(1, (per + 1) // 2)
                sel = band[:n_band]
                for k in sorted(fr, key=cost):
                    if len(sel) >= per:
                        break
                    if k not in sel:
                        sel.append(k)
                frontier[node] = sorted(sel, key=lambda k: -acc(k))

        keys = []
        i = 0
        while size is None or len(keys) < size:
            added = False
            for node in self.nodes:
                if i < len(frontier[node]):
                    k = frontier[node][i]
                    if k not in keys:
                        keys.append(k)
                    added = True
                    if size is not None and len(keys) >= size:
                        break
            if not added:
                break
            i += 1
        keyset = set(keys)

        pool = {}
        for g in self.groups:
            sel = [r for r in self.by_group[g] if r.key() in keyset]
            sel.sort(key=lambda r: (r.node, r.model))
            for i, r in enumerate(sel):
                r.idx = i
            pool[g] = sel
        self.pool_keys = keys
        return pool


def default_table_path():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, 'profiles', 'profile_table.csv')
