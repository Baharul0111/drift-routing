# Paired statistics over seeds: t-based intervals, a Wilcoxon signed-rank
# p-value, and the Holm correction the paper applies across its co-primary
# comparisons.
#
# With n = 10 seeds the exact two-sided Wilcoxon floor is 2/2^10 = 0.002, so
# no paired comparison at this n can report a smaller p-value.

import math


def mean(xs):
    return sum(xs) / float(len(xs))


def sd(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1.0))


# two-sided t critical values at 95%, indexed by degrees of freedom
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
        7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
        14: 2.145, 16: 2.120, 19: 2.093, 24: 2.064, 29: 2.045}


def t95(df):
    if df in _T95:
        return _T95[df]
    keys = sorted(_T95)
    for k in keys:
        if df < k:
            return _T95[k]
    return 1.96


def paired_ci(a, b):
    """95% CI on the mean paired difference a - b."""
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    if n < 2:
        return mean(d), mean(d), mean(d)
    half = t95(n - 1) * sd(d) / math.sqrt(n)
    m = mean(d)
    return m, m - half, m + half


def _norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def wilcoxon_p(a, b):
    """Two-sided signed-rank p-value, normal approximation with a floor.

    Exact enumeration is used below n = 11, where it matters: the smallest
    attainable two-sided p at n = 10 is 2/2^10.
    """
    d = [x - y for x, y in zip(a, b) if x != y]
    n = len(d)
    if n == 0:
        return 1.0
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    for r, i in enumerate(order):
        ranks[i] = r + 1.0
    w_plus = sum(ranks[i] for i in range(n) if d[i] > 0)

    if n <= 10:
        total = 1 << n
        count = 0
        for mask in range(total):
            s = sum(ranks[i] for i in range(n) if mask & (1 << i))
            if s <= min(w_plus, n * (n + 1) / 2.0 - w_plus) + 1e-9:
                count += 1
        return min(1.0, 2.0 * count / total)

    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    z = (w_plus - mu) / sigma if sigma else 0.0
    return max(2.0 / (1 << min(n, 30)), 2.0 * (1.0 - _norm_cdf(abs(z))))


def paired_t_p(a, b):
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    s = sd(d)
    if n < 2 or s == 0:
        return 1.0 if mean(d) == 0 else 0.0
    t = mean(d) / (s / math.sqrt(n))
    # normal approximation, adequate for reporting alongside the exact test
    return max(0.0, min(1.0, 2.0 * (1.0 - _norm_cdf(abs(t)))))


def holm(pvalues, alpha=0.05):
    """-> list of booleans, True where the hypothesis survives Holm."""
    idx = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    m = len(pvalues)
    out = [False] * m
    for rank, i in enumerate(idx):
        thresh = alpha / (m - rank)
        if pvalues[i] <= thresh:
            out[i] = True
        else:
            break
    return out


def compare(a, b, label=''):
    m, lo, hi = paired_ci(a, b)
    return {
        'label': label,
        'delta': m,
        'ci_lo': lo,
        'ci_hi': hi,
        'p_wilcoxon': wilcoxon_p(a, b),
        'p_paired_t': paired_t_p(a, b),
        'n': len(a),
    }
