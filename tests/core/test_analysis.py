"""Tests for sample_size.core.analysis."""
import io
import threading

import numpy as np
import pytest

from sample_size.core import analysis

PNG_MAGIC = b'\x89PNG'


def _csv(rows):
    return io.BytesIO('\n'.join(rows).encode())


def _conversion_csv(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    rows = ['bucket,converted']
    rows += [f'off,{int(rng.random() < .10)}' for _ in range(n)]
    rows += [f'on,{int(rng.random() < .15)}' for _ in range(n)]
    return _csv(rows)


def test_beta_analysis_summary_and_plot():
    """A conversion test returns a summary per bucket and a PNG."""
    result = analysis.analyze_csv(_conversion_csv(), 'converted', 'beta',
                                  random_state=0)
    assert result['rows'] == 4000
    assert result['control'] == 'off'
    assert {row['bucket'] for row in result['summary']} == {'off', 'on'}
    variant = next(r for r in result['summary'] if r['bucket'] == 'on')
    assert variant['prob_better'] > .9
    assert result['png'].startswith(PNG_MAGIC)


def test_numeric_bucket_labels_are_strings():
    """Bucket labels like 0 and 1 match the control typed into a form."""
    rows = ['bucket,value'] + [f'{i % 2},{i}' for i in range(200)]
    result = analysis.analyze_csv(_csv(rows), 'value', 'normal',
                                  control='0', random_state=0)
    assert result['control'] == '0'


def test_missing_column():
    """A column not in the file gives a readable error."""
    with pytest.raises(analysis.AnalysisError, match='Could not read'):
        analysis.analyze_csv(_csv(['bucket,x', 'off,1']), 'converted',
                             'beta')


def test_non_numeric_metric():
    """Text in the metric column is an analysis error."""
    with pytest.raises(analysis.AnalysisError, match='Could not read'):
        analysis.analyze_csv(_csv(['bucket,converted', 'off,yes']),
                             'converted', 'beta')


def test_row_limit(monkeypatch):
    """Files over the row limit are rejected."""
    monkeypatch.setattr(analysis, 'MAX_ROWS', 10)
    rows = ['bucket,converted'] + ['off,1'] * 11
    with pytest.raises(analysis.AnalysisError, match='more than 10 rows'):
        analysis.analyze_csv(_csv(rows), 'converted', 'beta')


def test_non_binary_beta_data_is_value_error():
    """BayesABTest's own validation errors reach the caller as ValueError."""
    rows = ['bucket,converted', 'off,2', 'on,1']
    with pytest.raises(ValueError, match='binary'):
        analysis.analyze_csv(_csv(rows), 'converted', 'beta')


def test_same_metric_and_group_column():
    """The metric and bucket columns must differ."""
    with pytest.raises(analysis.AnalysisError, match='different'):
        analysis.analyze_csv(_csv(['a', '1']), 'a', 'beta', group='a')


def test_unknown_family_and_prior():
    """Unknown options are rejected before reading the file."""
    with pytest.raises(analysis.AnalysisError, match='family'):
        analysis.analyze_csv(_csv([]), 'x', 'gamma')
    with pytest.raises(analysis.AnalysisError, match='prior'):
        analysis.analyze_csv(_csv([]), 'x', 'beta', prior='flat')


def test_busy_when_all_slots_taken(monkeypatch):
    """Analyses beyond the concurrency limit fail fast instead of queueing."""
    monkeypatch.setattr(analysis, '_slots', threading.BoundedSemaphore(1))
    analysis._slots.acquire()  # pylint: disable=protected-access
    with pytest.raises(analysis.Busy):
        analysis.analyze_csv(_conversion_csv(10), 'converted', 'beta')


def test_slot_released_after_error():
    """A failed analysis gives its slot back."""
    for _ in range(analysis.MAX_CONCURRENT + 1):
        with pytest.raises(analysis.AnalysisError):
            analysis.analyze_csv(_csv(['bucket,x', 'off,1']), 'converted',
                                 'beta')
