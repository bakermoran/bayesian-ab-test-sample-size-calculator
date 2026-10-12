"""Tests for the HTML views."""
import io

import pytest

from sample_size import create_app
from sample_size.core import analysis


@pytest.fixture(name='client')
def client_fixture():
    """Return a Flask test client."""
    return create_app({"TESTING": True}).test_client()


def test_home_page(client):
    """The landing page renders."""
    assert client.get('/').status_code == 200


def test_back_link_on_app_pages_not_home(client):
    """App pages link back to the home page; the home page has no link."""
    assert b'class="back-link"' not in client.get('/').data
    for path in ('/sample_size/', '/analyze/'):
        assert b'class="back-link" href="/"' in client.get(path).data


def test_sample_size_form_renders_without_params(client):
    """The form renders with no results or errors."""
    response = client.get('/sample_size/')
    assert response.status_code == 200
    assert b'Results' not in response.data


def test_sample_size_form_shows_results(client):
    """A valid submission renders results."""
    response = client.get('/sample_size/',
                          query_string={'baseline_conversion_rate': .1,
                                        'expected_relative_lift': .1})
    assert response.status_code == 200
    assert b'Results' in response.data


def test_sample_size_form_shows_lift_error(client):
    """A lift pushing the variant rate to 100% shows a field error."""
    response = client.get('/sample_size/',
                          query_string={'baseline_conversion_rate': .5,
                                        'expected_relative_lift': 1})
    assert response.status_code == 200
    assert b'expected_relative_lift' in response.data
    assert b'Results' not in response.data


def _upload(client, csv, **fields):
    data = {'file': (io.BytesIO(csv.encode()), 'results.csv'),
            'metric': 'converted', 'family': 'beta', **fields}
    return client.post('/analyze/', data=data,
                       content_type='multipart/form-data')


def _conversion_csv():
    rows = ['bucket,converted']
    rows += ['off,1'] * 100 + ['off,0'] * 900
    rows += ['on,1'] * 150 + ['on,0'] * 850
    return '\n'.join(rows)


def test_analyze_form_renders(client):
    """The upload form renders, with a Clear link back to a blank form."""
    response = client.get('/analyze/')
    assert response.status_code == 200
    assert b'href="/analyze/">Clear</a>' in response.data


def test_analyze_upload_shows_results(client):
    """A valid upload renders the summary and an inline plot."""
    response = _upload(client, _conversion_csv())
    assert response.status_code == 200
    assert b'Results' in response.data
    assert b'data:image/png;base64,' in response.data
    assert b'download="ab-test-report.png"' in response.data


def test_analyze_requires_file(client):
    """Submitting without a file shows an error."""
    response = client.post('/analyze/', data={'metric': 'converted'},
                           content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'Choose a CSV file' in response.data


def test_analyze_bad_column_shows_error(client):
    """A missing column is reported on the page."""
    response = _upload(client, _conversion_csv(), metric='revenue')
    assert response.status_code == 400
    assert b'Could not read the CSV' in response.data


def test_analyze_file_too_large():
    """An upload over the size limit renders the form with a 413."""
    app = create_app({'TESTING': True, 'MAX_CONTENT_LENGTH': 100})
    response = _upload(app.test_client(), _conversion_csv())
    assert response.status_code == 413
    assert b'File is over' in response.data


def test_analyze_busy_returns_503(client, monkeypatch):
    """A busy server tells the user to retry."""
    def busy(*_args, **_kwargs):
        raise analysis.Busy('The server is busy analyzing other files')
    monkeypatch.setattr(analysis, 'analyze_csv', busy)
    response = _upload(client, _conversion_csv())
    assert response.status_code == 503
    assert b'busy' in response.data
