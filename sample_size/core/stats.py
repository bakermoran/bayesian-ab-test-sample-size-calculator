"""Beta-distribution probability, loss, and sample size calculations."""
import numpy as np
import scipy.special as sc


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


def _posterior_params(sample_size, conversion_rate, prior_alpha, prior_beta):
    """Return Beta posterior (alpha, beta) for a sample at a conversion rate."""
    successes = int(round(sample_size * conversion_rate, 0))
    failures = int(round(sample_size * (1 - conversion_rate), 0))
    return successes + prior_alpha, failures + prior_beta


def _sample_size_fixed_loss_tolerance(baseline_conversion_rate,
                                      expected_relative_lift,
                                      loss_tolerance=0.05,
                                      prior_alpha=1,
                                      prior_beta=1):

    if expected_relative_lift <= 0:
        raise ValueError('expected_relative_lift must be greater than 0')

    variant_conversion_rate = baseline_conversion_rate * (
                               1 + expected_relative_lift)

    epsilon = baseline_conversion_rate * loss_tolerance

    b_risk = float('inf')
    sample_size = 0

    while b_risk > epsilon:
        sample_size += 10
        a, b = _posterior_params(sample_size, baseline_conversion_rate,
                                 prior_alpha, prior_beta)
        c, d = _posterior_params(sample_size, variant_conversion_rate,
                                 prior_alpha, prior_beta)

        b_risk = _loss_choose_b_over_a(a, b, c, d)

    context = {}
    context['loss_value'] = b_risk
    context['probability_B_over_A'] = _probability_b_beats_a(a, b, c, d)
    context['sample_size_per_variant'] = sample_size

    return context
