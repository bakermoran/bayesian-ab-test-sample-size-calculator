# AB Test Sample Size

A very simple calculator for a Bayesian sample size estimator for AB testing. At Root insurance, we switched from frequentist statistics to Bayesian statistics for AB testing for many reasons. You can read more about why we use Bayesian statistics [here](https://github.com/bakermoran/BayesABTest/blob/master/docs/besyian_ab_testing/Bayesian_AB_Testing_explainer.md).

## TL;DR

1. Bayesian statistics allows us to explain results better.
2. Frequestist statistics seeks to minimize the false positive rate; something that is largely unimportant in B2C AB testing. We instead seek to make many as many small gains as possibles.
3. It allows us to test faster. We can go with the result that we believe is _not worse_, because the decision is not high stakes.

That is, it _would_ allow us to test fast, if we were not still using [this](https://www.evanmiller.org/ab-testing/sample-size.html) sample size calculator, backed by frequentist statistics. Working on a team that has very limited access to data volume, we _need_ to take advantage of this quality of Bayesian statistics. I therefore set out to make my own sample size calculator in order to justify a smaller sample size.

## The Math

Each variant's conversion rate is modeled with a Beta posterior. With a $`\text{Beta}(\alpha_0, \beta_0)`$ prior and $`s`$ successes out of $`n`$ users:

```math
p \sim \text{Beta}(\alpha, \beta), \qquad \alpha = \alpha_0 + s, \qquad \beta = \beta_0 + (n - s)
```

Below, $`p_A \sim \text{Beta}(\alpha_A, \beta_A)`$ is the control, $`p_B \sim \text{Beta}(\alpha_B, \beta_B)`$ is the variant, and $`B(x, y)`$ is the [Beta function](https://en.wikipedia.org/wiki/Beta_function). All Beta functions are computed in log space (`scipy.special.betaln`) to avoid overflow.

### Probability B beats A

The exact closed form ([Evan Miller](https://www.evanmiller.org/bayesian-ab-testing.html)), valid for integer $`\alpha_B`$:

```math
P(p_B > p_A) = \sum_{i=0}^{\alpha_B - 1} \frac{B(\alpha_A + i,\ \beta_A + \beta_B)}{(\beta_B + i)\, B(1 + i,\ \beta_B)\, B(\alpha_A,\ \beta_A)}
```

### Expected loss

The expected loss of choosing B is the conversion rate we expect to give up if B is actually worse than A:

```math
\mathcal{L}(B) = \mathbb{E}\left[\max(p_A - p_B,\ 0)\right]
```

This has a closed form ([Chris Stucchio](https://www.chrisstucchio.com/blog/2014/bayesian_ab_decision_rule.html)) in terms of the probability above:

```math
\mathcal{L}(B) = \frac{B(\alpha_A + 1,\ \beta_A)}{B(\alpha_A,\ \beta_A)}\, P\big(p_A' > p_B\big) \;-\; \frac{B(\alpha_B + 1,\ \beta_B)}{B(\alpha_B,\ \beta_B)}\, P\big(p_A > p_B'\big)
```

where $`p_A' \sim \text{Beta}(\alpha_A + 1, \beta_A)`$ and $`p_B' \sim \text{Beta}(\alpha_B + 1, \beta_B)`$. This comes from splitting the expectation into $`\mathbb{E}[p_A \mathbf{1}\{p_A > p_B\}] - \mathbb{E}[p_B \mathbf{1}\{p_A > p_B\}]`$ and using $`\mathbb{E}[p\,\mathbf{1}\{\cdot\}] = \mathbb{E}[p]\, P'(\cdot)`$, where $`\mathbb{E}[p] = \frac{\alpha}{\alpha + \beta} = \frac{B(\alpha + 1, \beta)}{B(\alpha, \beta)}`$ and $`P'`$ is taken under the size-biased $`\text{Beta}(\alpha + 1, \beta)`$. The loss of choosing A, $`\mathcal{L}(A)`$, is the same formula with A and B swapped.

### Sample size

Given a baseline conversion rate $`c_A`$, an expected relative lift $`\ell`$, a relative loss tolerance $`\tau`$, and a power $`\pi`$ (default 0.8), the variant rate and loss threshold are:

```math
c_B = c_A (1 + \ell), \qquad \varepsilon = c_A \cdot \tau
```

The goal is the smallest per-variant sample size $`n`$ where, if B's true rate really is $`c_B`$, a fraction $`\pi`$ of experiments end with $`\mathcal{L}(B) \le \varepsilon`$. This is the Bayesian analog of power, sometimes called *assurance*.

**Planning outcome.** The observed difference $`\hat{c}_B - \hat{c}_A`$ is approximately normal around $`c_B - c_A`$ with variance $`\sigma^2 = \sigma_A^2 + \sigma_B^2`$, where $`\sigma_A^2 = c_A(1 - c_A)/n`$ and $`\sigma_B^2 = c_B(1 - c_B)/n`$. A fraction $`\pi`$ of experiments will see a difference at least $`z_\pi`$ standard deviations below the truth, so we plan for that outcome. The shift is split between the arms in proportion to their variances, which is the most likely way to observe that difference:

```math
\hat{c}_A = c_A + z_\pi \frac{\sigma_A^2}{\sigma}, \qquad \hat{c}_B = c_B - z_\pi \frac{\sigma_B^2}{\sigma}, \qquad z_\pi = \Phi^{-1}(\pi)
```

At $`\pi = 0.5`$, $`z_\pi = 0`$ and this is just the expected data. The posteriors use these rates as fractional counts, so the loss changes smoothly with $`n`$:

```math
p_A \sim \text{Beta}\big(\alpha_0 + n \hat{c}_A,\ \beta_0 + n (1 - \hat{c}_A)\big), \qquad p_B \sim \text{Beta}\big(\alpha_0 + n \hat{c}_B,\ \beta_0 + n (1 - \hat{c}_B)\big)
```

**Computing the loss.** The closed form above needs integer $`\alpha_B`$ and costs $`O(\alpha_B)`$, so the search uses an equivalent one-dimensional integral instead. Its cost doesn't depend on $`n`$:

```math
\mathcal{L}(B) = \int_0^1 F_B(t)\,\big(1 - F_A(t)\big)\, dt
```

Here $`F`$ is the Beta CDF (`scipy.special.betainc`). This holds because $`\max(a - b, 0) = \int_0^1 \mathbf{1}\{b < t < a\}\, dt`$. The integral runs only over the interval holding all but $`10^{-12}`$ of each posterior's mass.

**Search.** The loss decreases with $`n`$, so we double $`n`$ until $`\mathcal{L}(B) \le \varepsilon`$ and then root-find (`scipy.optimize.brentq`) in between. The result is rounded up to a multiple of 10:

```math
n^* = \min \left\{ n \in \{10, 20, 30, \dots\} : \mathcal{L}(B) \le \varepsilon \right\}
```

The reported `loss_value` and `probability_B_over_A` are evaluated at this planning outcome for $`n^*`$. Sample sizes over $`10^9`$ per variant are rejected: the integrals lose precision there, and no real test is that large.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run flask run
uv run ruff check .
uv run pylint sample_size
```
