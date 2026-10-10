"""Tests for sample_size.core.stats."""
import numpy as np
import pytest
from scipy import integrate, stats

from sample_size.core.stats import (
    _frequentist_sample_size,
    _loss_choose_b_over_a,
    _loss_choose_b_over_a_quad,
    _observed_rates,
    _posterior_params,
    _probability_b_beats_a,
    _probability_b_beats_a_quad,
    _sample_size_fixed_loss_tolerance,
)

N_DRAWS = 400_000


@pytest.fixture(name="draws")
def draws_fixture():
    """Return a seeded random generator for Monte Carlo cross-checks."""
    return np.random.default_rng(1234)


def test_probability_identical_distributions_is_half():
    """Two identical posteriors are equally likely to win."""
    assert _probability_b_beats_a(20, 80, 20, 80) == pytest.approx(0.5)


def test_probability_is_complementary():
    """P(B > A) + P(A > B) == 1."""
    forward = _probability_b_beats_a(10, 90, 14, 86)
    reverse = _probability_b_beats_a(14, 86, 10, 90)
    assert forward + reverse == pytest.approx(1.0)


def test_probability_favors_higher_rate():
    """The variant with the higher conversion rate is more likely to win."""
    assert _probability_b_beats_a(10, 90, 20, 80) > 0.5
    assert _probability_b_beats_a(20, 80, 10, 90) < 0.5


def test_probability_matches_monte_carlo(draws):
    """Closed form agrees with sampling from the Beta distributions."""
    a_samples = draws.beta(10, 90, N_DRAWS)
    b_samples = draws.beta(15, 85, N_DRAWS)
    expected = np.mean(b_samples > a_samples)
    assert _probability_b_beats_a(10, 90, 15, 85) == pytest.approx(
        expected, abs=0.005)


def test_loss_is_non_negative():
    """Expected loss can never be negative."""
    assert _loss_choose_b_over_a(10, 90, 15, 85) >= 0
    assert _loss_choose_b_over_a(15, 85, 10, 90) >= 0


def test_loss_lower_when_b_is_better():
    """Choosing B costs less when B has the higher conversion rate."""
    assert (_loss_choose_b_over_a(10, 90, 20, 80)
            < _loss_choose_b_over_a(20, 80, 10, 90))


def test_loss_matches_monte_carlo(draws):
    """Loss equals E[max(A - B, 0)] under the posteriors."""
    a_samples = draws.beta(10, 90, N_DRAWS)
    b_samples = draws.beta(15, 85, N_DRAWS)
    expected = np.mean(np.maximum(a_samples - b_samples, 0))
    assert _loss_choose_b_over_a(10, 90, 15, 85) == pytest.approx(
        expected, abs=0.001)


def test_posterior_params_adds_prior():
    """Posterior is successes/failures plus the prior."""
    assert _posterior_params(100, 0.1, 1, 1) == pytest.approx((11, 91))


def test_posterior_params_keeps_fractional_counts():
    """Counts are not rounded, so the loss is smooth in sample size."""
    assert _posterior_params(10, 0.25, 0, 0) == pytest.approx((2.5, 7.5))


@pytest.mark.parametrize('lift', [0, -0.1])
def test_sample_size_rejects_non_positive_lift(lift):
    """A lift of zero or less is invalid."""
    with pytest.raises(ValueError, match='greater than 0'):
        _sample_size_fixed_loss_tolerance(0.1, lift)


def test_sample_size_result_shape_and_tolerance():
    """Result has the expected keys and meets the loss tolerance."""
    result = _sample_size_fixed_loss_tolerance(0.1, 0.2, loss_tolerance=0.05)
    assert set(result) == {
        'loss_value', 'probability_B_over_A', 'sample_size_per_variant'}
    assert result['sample_size_per_variant'] % 10 == 0
    assert result['loss_value'] <= 0.1 * 0.05
    assert 0.5 < result['probability_B_over_A'] <= 1


def test_sample_size_shrinks_with_larger_lift():
    """Bigger expected lifts need fewer samples."""
    small = _sample_size_fixed_loss_tolerance(0.1, 0.1)
    large = _sample_size_fixed_loss_tolerance(0.1, 0.5)
    assert large['sample_size_per_variant'] < small['sample_size_per_variant']


def test_sample_size_grows_with_tighter_tolerance():
    """A stricter loss tolerance needs more samples."""
    loose = _sample_size_fixed_loss_tolerance(0.1, 0.2, loss_tolerance=0.10)
    tight = _sample_size_fixed_loss_tolerance(0.1, 0.2, loss_tolerance=0.02)
    assert tight['sample_size_per_variant'] > loose['sample_size_per_variant']


def test_probability_matches_exact_integration():
    """Closed form agrees with numerical integration of the Beta CDF."""
    expected, _ = integrate.quad(
        lambda x: stats.beta.pdf(x, 15, 85) * stats.beta.cdf(x, 10, 90),
        0, 1)
    assert _probability_b_beats_a(10, 90, 15, 85) == pytest.approx(
        expected, abs=1e-9)


def test_loss_matches_exact_integration():
    """Loss agrees with numerical integration of E[max(A - B, 0)]."""
    expected, _ = integrate.dblquad(
        lambda b, a: (a - b) * stats.beta.pdf(a, 10, 90)
        * stats.beta.pdf(b, 15, 85),
        0, 1, 0, lambda a: a)
    assert _loss_choose_b_over_a(10, 90, 15, 85) == pytest.approx(
        expected, abs=1e-9)


def test_loss_finite_for_large_samples():
    """Large, well-separated posteriors don't produce nan or inf."""
    loss = _loss_choose_b_over_a(500, 9500, 700, 9300)
    assert np.isfinite(loss)
    assert loss >= 0


PARAMS = [(10, 90, 15, 85), (1, 1, 1, 1), (90, 10, 85, 15),
          (500, 9500, 700, 9300), (15000, 135000, 15200, 134800)]


@pytest.mark.parametrize('params', PARAMS)
def test_quad_probability_matches_closed_form(params):
    """Numerical integration agrees with the closed-form sum."""
    assert _probability_b_beats_a_quad(*params) == pytest.approx(
        _probability_b_beats_a(*params), abs=1e-9)


@pytest.mark.parametrize('params', PARAMS)
def test_quad_loss_matches_closed_form(params):
    """Numerical integration agrees with the closed-form loss."""
    swapped = params[2:] + params[:2]
    assert _loss_choose_b_over_a_quad(*params) == pytest.approx(
        _loss_choose_b_over_a(*params), abs=1e-10)
    assert _loss_choose_b_over_a_quad(*swapped) == pytest.approx(
        _loss_choose_b_over_a(*swapped), abs=1e-10)


def test_quad_handles_fractional_params(draws):
    """Non-integer parameters agree with Monte Carlo."""
    a_samples = draws.beta(10.5, 90.25, N_DRAWS)
    b_samples = draws.beta(15.75, 85.5, N_DRAWS)
    assert _probability_b_beats_a_quad(10.5, 90.25, 15.75, 85.5) == (
        pytest.approx(np.mean(b_samples > a_samples), abs=0.005))
    assert _loss_choose_b_over_a_quad(10.5, 90.25, 15.75, 85.5) == (
        pytest.approx(np.mean(np.maximum(a_samples - b_samples, 0)),
                      abs=0.001))


def test_observed_rates_at_half_power_are_true_rates():
    """At 50% power the planning outcome is the expected data."""
    assert _observed_rates(1000, 0.1, 0.12, 0.5) == pytest.approx((0.1, 0.12))


def test_observed_rates_shrink_difference_with_power():
    """Higher power plans for a smaller observed difference."""
    rate_a, rate_b = _observed_rates(1000, 0.1, 0.12, 0.8)
    assert rate_a > 0.1
    assert rate_b < 0.12


@pytest.mark.parametrize('power', [0, 1, 1.5])
def test_sample_size_rejects_invalid_power(power):
    """Power must be strictly between 0 and 1."""
    with pytest.raises(ValueError, match='power'):
        _sample_size_fixed_loss_tolerance(0.1, 0.1, power=power)


def test_sample_size_rejects_huge_sample_sizes():
    """Inputs needing over a billion per variant are rejected."""
    with pytest.raises(ValueError, match='sample size'):
        _sample_size_fixed_loss_tolerance(1e-4, 1e-4, 1e-4)


def test_sample_size_grows_with_power():
    """More power needs more samples."""
    sizes = [_sample_size_fixed_loss_tolerance(0.1, 0.1, 0.002, power=power)[
        'sample_size_per_variant'] for power in (0.5, 0.8, 0.9)]
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == 3


@pytest.mark.parametrize('base,lift,tol,power', [
    (0.1, 0.2, 0.05, 0.8),
    (0.1, 0.1, 0.002, 0.5),
    (0.1, 0.1, 0.002, 0.8),
    (0.05, 0.05, 0.002, 0.8),
    (0.3, 0.02, 0.001, 0.8),
    (0.1, 0.1, 0.002, 0.9),
])
def test_sample_size_achieves_power(draws, base, lift, tol, power):
    """Simulated experiments meet the tolerance at about the given power."""
    size = _sample_size_fixed_loss_tolerance(
        base, lift, tol, power=power)['sample_size_per_variant']
    successes_a = draws.binomial(size, base, 2000)
    successes_b = draws.binomial(size, base * (1 + lift), 2000)
    hits = [
        _loss_choose_b_over_a(s_a + 1, size - s_a + 1, s_b + 1,
                              size - s_b + 1) <= base * tol
        for s_a, s_b in zip(successes_a, successes_b)]
    assert np.mean(hits) == pytest.approx(power, abs=0.03)


@pytest.mark.parametrize('power', [0.5, 0.8])
def test_sample_size_is_smallest_that_meets_tolerance(power):
    """The reported size meets tolerance and one step smaller does not."""
    base, lift, tol = 0.1, 0.2, 0.05
    result = _sample_size_fixed_loss_tolerance(base, lift, tol, power=power)
    size = result['sample_size_per_variant']
    epsilon = base * tol

    def loss_at(n):
        rate_a, rate_b = _observed_rates(n, base, base * (1 + lift), power)
        return _loss_choose_b_over_a_quad(*_posterior_params(n, rate_a, 1, 1),
                                          *_posterior_params(n, rate_b, 1, 1))

    assert loss_at(size) <= epsilon
    assert loss_at(size - 10) > epsilon
    assert result['loss_value'] == pytest.approx(loss_at(size))


def test_frequentist_sample_size_matches_evan_miller():
    """5% baseline, +20% relative lift is ~8,200 per variant at 80% power."""
    assert _frequentist_sample_size(0.05, 0.2) == pytest.approx(8150, abs=100)


def test_frequentist_sample_size_invalid_lift():
    """A non-positive lift has no sample size."""
    with pytest.raises(ValueError):
        _frequentist_sample_size(0.05, 0)
