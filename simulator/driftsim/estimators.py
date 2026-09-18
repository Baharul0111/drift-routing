# Content estimators. They predict the object-count group of an incoming
# frame; the router then reads that group's row out of the static profile.
#
# The oracle sees the true group. The three deployed estimators are
# calibrated noise channels whose confusion matrices reproduce the accuracy
# and bias reported for ECORE's edge-detection, output-based and SSD
# front ends.


class Estimator(object):
    name = 'oracle'
    accuracy = 1.0
    bias = 0.0
    cost_mWh = 0.0

    def __init__(self, groups, rng):
        self.groups = list(groups)
        self.rng = rng

    def estimate(self, true_group):
        if self.rng.random() < self.accuracy:
            return true_group
        i = self.groups.index(true_group)
        step = 1 if self.rng.random() < 0.5 + self.bias else -1
        j = min(len(self.groups) - 1, max(0, i + step))
        return self.groups[j]


class Oracle(Estimator):
    name = 'oracle'
    accuracy = 1.0


class EdgeDetection(Estimator):
    # cheapest front end, least accurate, biased towards over-counting
    name = 'ed'
    accuracy = 0.82
    bias = 0.18
    cost_mWh = 0.0021


class OutputBased(Estimator):
    # reuses the previous frame's detections, so it lags a scene change
    name = 'ob'
    accuracy = 0.88
    bias = 0.06
    cost_mWh = 0.0

    def __init__(self, groups, rng):
        Estimator.__init__(self, groups, rng)
        self.prev = None

    def estimate(self, true_group):
        g = Estimator.estimate(self, true_group)
        out = self.prev if self.prev is not None else g
        self.prev = g
        return out


class SSDFrontEnd(Estimator):
    # a real detector as the front end: accurate, and expensive enough that
    # its gateway cost dominates at 30 req/s
    name = 'sf'
    accuracy = 0.96
    bias = 0.02
    cost_mWh = 0.355


ESTIMATORS = {
    'oracle': Oracle,
    'ed': EdgeDetection,
    'ob': OutputBased,
    'sf': SSDFrontEnd,
}


def make(name, groups, rng):
    return ESTIMATORS[name](groups, rng)
