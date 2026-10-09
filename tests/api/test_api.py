"""Tests for the v1 REST API."""
import pytest

from sample_size import app


@pytest.fixture(name='client')
def client_fixture():
    """Return a Flask test client."""
    return app.test_client()


def test_index_serves_openapi_spec(client):
    """Index route serves the OpenAPI spec covering every service."""
    response = client.get('/api/v1/')
    assert response.status_code == 200
    assert response.json['openapi'].startswith('3.')
    assert set(response.json['paths']) == {'/api/v1/sample_size/',
                                           '/api/v1/loss_function/'}


def test_docs_page(client):
    """Docs page renders."""
    assert client.get('/api/docs').status_code == 200


def test_loss_function_symmetric_inputs(client):
    """Identical variants give a 50/50 probability."""
    response = client.get('/api/v1/loss_function/',
                          query_string={'alpha_A': 10, 'beta_A': 90,
                                        'alpha_B': 10, 'beta_B': 90})
    assert response.status_code == 200
    outputs = response.json
    assert outputs['probability_B_greater_than_A'] == pytest.approx(.5)
    assert outputs['choose_variant_A'] == pytest.approx(
        outputs['choose_variant_B'])


def test_loss_function_missing_param(client):
    """Missing params return a JSON 400."""
    response = client.get('/api/v1/loss_function/', query_string={'alpha_A': 1})
    assert response.status_code == 400
    assert 'beta_A' in response.json['errors']


def test_sample_size_invalid_lift(client):
    """A lift pushing the variant rate to 100% or more is rejected."""
    response = client.get('/api/v1/sample_size/',
                          query_string={'baseline_conversion_rate': .5,
                                        'expected_relative_lift': 1})
    assert response.status_code == 400
    assert 'expected_relative_lift' in response.json['errors']


def test_sample_size_defaults_to_80_percent_power(client):
    """Omitting power gives the same result as passing 0.8."""
    params = {'baseline_conversion_rate': .1, 'expected_relative_lift': .1}
    default = client.get('/api/v1/sample_size/', query_string=params)
    explicit = client.get('/api/v1/sample_size/',
                          query_string={**params, 'power': .8})
    assert default.status_code == 200
    assert default.json == explicit.json
    assert default.json['sample_size_per_variant'] > 0


def test_sample_size_more_power_needs_more_samples(client):
    """Raising power raises the sample size."""
    def size(power):
        response = client.get('/api/v1/sample_size/',
                              query_string={'baseline_conversion_rate': .1,
                                            'expected_relative_lift': .1,
                                            'power': power})
        return response.json['sample_size_per_variant']
    assert size(.9) > size(.5)


@pytest.mark.parametrize('power', [.4, 1])
def test_sample_size_invalid_power(client, power):
    """Power outside [0.5, 1) is rejected."""
    response = client.get('/api/v1/sample_size/',
                          query_string={'baseline_conversion_rate': .1,
                                        'expected_relative_lift': .1,
                                        'power': power})
    assert response.status_code == 400
    assert 'power' in response.json['errors']


def test_sample_size_too_large(client):
    """Inputs needing an impractical sample size return a JSON 400."""
    response = client.get('/api/v1/sample_size/',
                          query_string={'baseline_conversion_rate': 1e-4,
                                        'expected_relative_lift': 1e-4,
                                        'loss_tolerance': 1e-4})
    assert response.status_code == 400
    assert 'sample size' in response.json['message']
