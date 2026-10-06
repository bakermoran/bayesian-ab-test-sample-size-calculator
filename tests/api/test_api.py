"""Tests for the v1 REST API."""
import pytest

from sample_size import app


@pytest.fixture(name='client')
def client_fixture():
    """Return a Flask test client."""
    return app.test_client()


def test_index_lists_services(client):
    """Index route lists the available services."""
    response = client.get('/api/v1/')
    assert response.status_code == 200
    assert set(response.json['available_services']) == {'sample_size',
                                                        'loss_function'}


def test_loss_function_symmetric_inputs(client):
    """Identical variants give a 50/50 probability."""
    response = client.get('/api/v1/loss_function/',
                          query_string={'alpha_A': 10, 'beta_A': 90,
                                        'alpha_B': 10, 'beta_B': 90})
    assert response.status_code == 200
    outputs = response.json['outputs']
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
