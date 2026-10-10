"""Beta-distribution probability, loss, and sample size calculations."""
import numpy as np
import scipy.special as sc
from scipy import integrate, optimize, stats

# Posterior mass outside these quantiles is ignored when integrating
_TAIL = 1e-12
# Beyond this the integrals lose precision, and no real test is this large
_MAX_SAMPLE_SIZE = 10**9


def _probability_b_beats_a(alpha_a, beta_a, alpha_b, beta_b):
    """Calculate the probablty that a Beta distributions is greater.

    Arguments:
        alpha_a {int} -- Beta_A alpha param
        beta_a {int} -- Beta_A beta param
        alpha_b {int} -- Beta_B alpha param
        beta_b {int} -- Beta_B beta param

    Returns:
        float -- probabilty that Beta_B(alpha_b, beta_b) is greater
          than Beta_A(alpha_a, beta_a)
    """
    i = np.arange(alpha_b)
    return float(np.exp(sc.betaln(alpha_a + i, beta_b + beta_a) -
                        np.log(beta_b + i) -
                        sc.betaln(1 + i, beta_b) -
                        sc.betaln(alpha_a, beta_a)).sum())


def _loss_choose_b_over_a(alpha_a, beta_a, alpha_b, beta_b):
    """Calc the expected loss of choosing B over A.

    Beta_A is Beta(alpha_a, beta_a) and Beta_B is Beta(alpha_b, beta_b).

    Arguments:
        alpha_a {int} -- Beta_A alpha param
        beta_a {int} -- Beta_A beta param
        alpha_b {int} -- Beta_B alpha param
        beta_b {int} -- Beta_B beta param

    Returns:
        float -- the loss function value for Beta_B over Beta_A
    """
    x1 = sc.betaln(alpha_a + 1, beta_a)
    # P(A' > B) computed directly; 1 - P(B > A') loses precision near 1
    y1 = np.log(_probability_b_beats_a(alpha_b, beta_b, alpha_a + 1, beta_a))
    z1 = sc.betaln(alpha_a, beta_a)

    x2 = sc.betaln(alpha_b + 1, beta_b)
    y2 = np.log(_probability_b_beats_a(alpha_b + 1, beta_b, alpha_a, beta_a))
    z2 = sc.betaln(alpha_b, beta_b)

    return float(np.exp(x1 + y1 - z1) - np.exp(x2 + y2 - z2))


def _integration_bounds(alpha_a, beta_a, alpha_b, beta_b):
    """Return an interval holding essentially all mass of both posteriors."""
    lower = min(sc.betaincinv(alpha_a, beta_a, _TAIL),
                sc.betaincinv(alpha_b, beta_b, _TAIL))
    upper = max(sc.betaincinv(alpha_a, beta_a, 1 - _TAIL),
                sc.betaincinv(alpha_b, beta_b, 1 - _TAIL))
    return lower, upper


def _probability_b_beats_a_quad(alpha_a, beta_a, alpha_b, beta_b):
    """Calculate P(Beta_B > Beta_A) by numerical integration.

    Uses P(B > A) = integral of f_B(t) * F_A(t) dt. Unlike the closed form,
    this accepts non-integer parameters and costs the same at any sample size.

    Arguments:
        alpha_a {float} -- Beta_A alpha param
        beta_a {float} -- Beta_A beta param
        alpha_b {float} -- Beta_B alpha param
        beta_b {float} -- Beta_B beta param

    Returns:
        float -- probabilty that Beta_B(alpha_b, beta_b) is greater
          than Beta_A(alpha_a, beta_a)
    """
    lower, upper = _integration_bounds(alpha_a, beta_a, alpha_b, beta_b)
    return integrate.quad(
        lambda t: (stats.beta.pdf(t, alpha_b, beta_b)
                   * sc.betainc(alpha_a, beta_a, t)),
        lower, upper, epsabs=1e-13, epsrel=1e-10, limit=200)[0]


def _loss_choose_b_over_a_quad(alpha_a, beta_a, alpha_b, beta_b):
    """Calc the expected loss of choosing B over A by numerical integration.

    Uses E[max(A - B, 0)] = integral of F_B(t) * (1 - F_A(t)) dt, since
    max(a - b, 0) is the length of the interval (b, a). Unlike the closed
    form, this accepts non-integer parameters and costs the same at any
    sample size.

    Arguments:
        alpha_a {float} -- Beta_A alpha param
        beta_a {float} -- Beta_A beta param
        alpha_b {float} -- Beta_B alpha param
        beta_b {float} -- Beta_B beta param

    Returns:
        float -- the loss function value for Beta_B over Beta_A
    """
    lower, upper = _integration_bounds(alpha_a, beta_a, alpha_b, beta_b)
    return integrate.quad(
        lambda t: (sc.betainc(alpha_b, beta_b, t)
                   * sc.betaincc(alpha_a, beta_a, t)),
        lower, upper, epsabs=1e-15, epsrel=1e-10, limit=200)[0]


def _posterior_params(sample_size, conversion_rate, prior_alpha, prior_beta):
    """Return Beta posterior (alpha, beta) for a sample at a conversion rate.

    Counts are left fractional so the loss changes smoothly with sample size.
    """
    successes = sample_size * conversion_rate
    return successes + prior_alpha, sample_size - successes + prior_beta


def _observed_rates(sample_size, baseline_rate, variant_rate, power):
    """Return the observed (A, B) rates at the 1 - power quantile outcome.

    The observed difference B - A is approximately normal around the true
    difference. Moving it down by z_power standard deviations gives an
    outcome that a fraction `power` of experiments will beat. The shift is
    split between the arms by their variances, the most likely way to get
    that difference. At power = 0.5 these are just the true rates.
    """
    var_a = baseline_rate * (1 - baseline_rate) / sample_size
    var_b = variant_rate * (1 - variant_rate) / sample_size
    shift = stats.norm.ppf(power) / np.sqrt(var_a + var_b)
    rate_a = np.clip(baseline_rate + shift * var_a, 0, 1)
    rate_b = np.clip(variant_rate - shift * var_b, 0, 1)
    return float(rate_a), float(rate_b)


def _sample_size_fixed_loss_tolerance(baseline_conversion_rate,
                                      expected_relative_lift,
                                      loss_tolerance=0.05,
                                      power=0.8,
                                      prior_alpha=1,
                                      prior_beta=1):
    """Find the per-variant sample size where choosing B is cheap enough.

    If B's true rate is baseline * (1 + lift), a fraction `power` of
    experiments of the returned size end with an expected loss of choosing B
    at or below baseline * loss_tolerance.

    Returns:
        dict -- sample_size_per_variant (a multiple of 10), plus the
          loss_value and probability_B_over_A at the 1 - power quantile
          outcome for that sample size
    """
    if expected_relative_lift <= 0:
        raise ValueError('expected_relative_lift must be greater than 0')
    if not 0 < power < 1:
        raise ValueError('power must be between 0 and 1')

    variant_conversion_rate = baseline_conversion_rate * (
                               1 + expected_relative_lift)

    epsilon = baseline_conversion_rate * loss_tolerance

    def posteriors(sample_size):
        rate_a, rate_b = _observed_rates(sample_size, baseline_conversion_rate,
                                         variant_conversion_rate, power)
        return (*_posterior_params(sample_size, rate_a, prior_alpha,
                                   prior_beta),
                *_posterior_params(sample_size, rate_b, prior_alpha,
                                   prior_beta))

    def excess_loss(sample_size):
        return _loss_choose_b_over_a_quad(*posteriors(sample_size)) - epsilon

    # Double until the loss is within tolerance, then root-find in between
    upper = 10
    while excess_loss(upper) > 0:
        if upper >= _MAX_SAMPLE_SIZE:
            raise ValueError('required sample size is over '
                             f'{_MAX_SAMPLE_SIZE:,} per variant')
        upper = min(2 * upper, _MAX_SAMPLE_SIZE)
    root = upper
    if upper > 10:
        root = optimize.brentq(excess_loss, upper / 2, upper, xtol=0.5)

    # Snap to the smallest multiple of 10 that meets the tolerance
    sample_size = max(10, int(np.ceil(root / 10)) * 10)
    while excess_loss(sample_size) > 0:
        sample_size += 10
    while sample_size > 10 and excess_loss(sample_size - 10) <= 0:
        sample_size -= 10

    params = posteriors(sample_size)
    context = {}
    context['loss_value'] = _loss_choose_b_over_a_quad(*params)
    context['probability_B_over_A'] = _probability_b_beats_a_quad(*params)
    context['sample_size_per_variant'] = sample_size

    return context


def _frequentist_sample_size(baseline_conversion_rate, expected_relative_lift,
                             power=0.8, significance=0.05):
    """Find the per-variant sample size for a two-sided two-proportion z-test.

    This is the classic frequentist calculation (e.g. Evan Miller's), using
    the unpooled normal approximation.

    Returns:
        int -- sample size per variant, rounded up to a multiple of 10 to
          match the Bayesian estimate
    """
    if expected_relative_lift <= 0:
        raise ValueError('expected_relative_lift must be greater than 0')
    if not 0 < power < 1:
        raise ValueError('power must be between 0 and 1')

    rate_a = baseline_conversion_rate
    rate_b = rate_a * (1 + expected_relative_lift)
    z_total = stats.norm.ppf(1 - significance / 2) + stats.norm.ppf(power)
    sample_size = (z_total ** 2 * (rate_a * (1 - rate_a)
                                   + rate_b * (1 - rate_b))
                   / (rate_b - rate_a) ** 2)
    return max(10, int(np.ceil(sample_size / 10)) * 10)
