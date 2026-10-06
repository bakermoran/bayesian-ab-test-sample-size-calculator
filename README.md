# AB Test Sample Size

A very simple calculator for a Bayesian sample size estimator for AB testing. At Root insurance, we switched from frequentist statistics to Bayesian statistics for AB testing for many reasons. You can read more about why we use Bayesian statistics [here](https://github.com/bakermoran/BayesABTest/blob/master/docs/besyian_ab_testing/Bayesian_AB_Testing_explainer.md).

## TL;DR

1. Bayesian statistics allows us to explain results better.
2. Frequestist statistics seeks to minimize the false positive rate; something that is largely unimportant in B2C AB testing. We instead seek to make many as many small gains as possibles.
3. It allows us to test faster. We can go with the result that we believe is _not worse_, because the decision is not high stakes.

That is, it _would_ allow us to test fast, if we were not still using [this](https://www.evanmiller.org/ab-testing/sample-size.html) sample size calculator, backed by frequentist statistics. Working on a team that has very limited access to data volume, we _need_ to take advantage of this quality of Bayesian statistics. I therefore set out to make my own sample size calculator in order to justify a smaller sample size.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run flask run
uv run ruff check .
uv run pylint sample_size
```
