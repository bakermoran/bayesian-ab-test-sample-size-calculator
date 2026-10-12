"""Analyze an uploaded experiment CSV with BayesABTest."""
import io
import threading

import matplotlib
import pandas as pd
from BayesABTest import ABTest, priors
from matplotlib import pyplot as plt

# No display on the server; must be set before any figure is created
matplotlib.use('Agg')

# Rows beyond this are rejected, bounding the memory a parse can use
MAX_ROWS = 500_000
# Analyses allowed at once, so a burst can't push a small host into swap
MAX_CONCURRENT = 2

FAMILIES = ('beta', 'poisson', 'normal', 'log-normal')
PRIORS = {'empirical': priors.Empirical, 'uninformed': priors.Uninformed}

_slots = threading.BoundedSemaphore(MAX_CONCURRENT)
# pyplot keeps global figure state, so only one thread may draw at a time
_plot_lock = threading.Lock()


class AnalysisError(ValueError):
    """The upload or options can't be analyzed; the message says why."""


class Busy(RuntimeError):
    """Too many analyses are running; try again shortly."""


def _read_csv(file, metric, group):
    """Read just the metric and group columns, enforcing the row limit."""
    if metric == group:
        raise AnalysisError('metric and group must be different columns')
    try:
        data = pd.read_csv(file, usecols=[metric, group], nrows=MAX_ROWS + 1,
                           dtype={metric: float, group: str})
    except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise AnalysisError(f'Could not read the CSV: {error}') from error
    if len(data) > MAX_ROWS:
        raise AnalysisError(f'The file has more than {MAX_ROWS:,} rows')
    return data


def _figure_png(result):
    """Render the full report for a fit result as PNG bytes."""
    with _plot_lock:
        figure = result.plot()
        try:
            buffer = io.BytesIO()
            figure.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        finally:
            plt.close(figure)
    return buffer.getvalue()


def analyze_csv(file, metric, family, *, group='bucket', control='off',  # pylint: disable=too-many-arguments
                prior='empirical', random_state=None):
    """Fit a Bayesian AB test to a CSV with a metric and a bucket column.

    Arguments:
        file -- binary file-like object holding the CSV, read in memory
        metric -- name of the column holding the response
        family -- 'beta', 'poisson', 'normal' or 'log-normal'

    Raises:
        Busy -- too many analyses are already running
        AnalysisError -- the file or options can't be analyzed
        ValueError -- BayesABTest rejected the data, e.g. non-binary values
          for the beta family

    Returns:
        dict -- rows analyzed, the family, a summary per bucket (name, mean, ci_low,
          ci_high, median_lift, prob_better), and the PNG report
    """
    if family not in FAMILIES:
        raise AnalysisError(f'family must be one of {list(FAMILIES)}')
    if prior not in PRIORS:
        raise AnalysisError(f'prior must be one of {list(PRIORS)}')
    if not _slots.acquire(blocking=False):  # pylint: disable=consider-using-with
        raise Busy('The server is busy analyzing other files')
    try:
        data = _read_csv(file, metric, group)
        test = ABTest(metric, family, control=control, group=group,
                      prior=PRIORS[prior](), random_state=random_state)
        result = test.fit(data)
        summary = result.summary().rename_axis('bucket').reset_index()
        return {'rows': len(data),
                'family': family,
                'control': result.control,
                'summary': summary.to_dict('records'),
                'png': _figure_png(result)}
    finally:
        _slots.release()
