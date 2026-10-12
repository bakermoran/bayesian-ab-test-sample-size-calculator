"""Sample size estimate for a Bayesian AB test, compared to frequentist."""
from sample_size.core import stats


class InputError(ValueError):
    """An input is invalid; `field` names the offending parameter."""

    def __init__(self, field, message):
        """Store the name of the invalid parameter."""
        super().__init__(message)
        self.field = field


def estimate_sample_size(baseline_conversion_rate, expected_relative_lift,
                         loss_tolerance=.002, power=.8, prior_alpha=1,
                         prior_beta=1):
    """Estimate the per-variant sample size, and compare it to frequentist.

    Raises:
        InputError -- the lift pushes the variant conversion rate to 100% or
          more
        ValueError -- another input is out of range, or the required sample
          size is impractically large

    Returns:
        dict -- sample_size_per_variant, loss_value and probability_B_over_A
          from the Bayesian calculation, plus frequentist_sample_size and
          sample_size_ratio (Bayesian over frequentist)
    """
    if baseline_conversion_rate * (1 + expected_relative_lift) >= 1:
        raise InputError('expected_relative_lift',
                         'baseline_conversion_rate * (1 + '
                         'expected_relative_lift) must be less than 1')
    results = stats.sample_size_fixed_loss_tolerance(
        baseline_conversion_rate=baseline_conversion_rate,
        expected_relative_lift=expected_relative_lift,
        loss_tolerance=loss_tolerance, power=power,
        prior_alpha=prior_alpha, prior_beta=prior_beta)
    frequentist = stats.frequentist_sample_size(
        baseline_conversion_rate, expected_relative_lift, power)
    results['frequentist_sample_size'] = frequentist
    results['sample_size_ratio'] = (
        results['sample_size_per_variant'] / frequentist)
    return results
