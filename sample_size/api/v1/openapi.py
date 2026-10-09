"""OpenAPI spec for v1, generated from the webargs schemas, and a docs page."""
import flask
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from marshmallow import Schema, fields

from sample_size.api.v1.loss_function import LOSS_FUNCTION_ARGS
from sample_size.api.v1.sample_size import SAMPLE_SIZE_ARGS

bp = flask.Blueprint('openapi', __name__)

SampleSizeQuery = Schema.from_dict(SAMPLE_SIZE_ARGS, name='SampleSizeQuery')
LossFunctionQuery = Schema.from_dict(LOSS_FUNCTION_ARGS,
                                     name='LossFunctionQuery')


class SampleSizeResponse(Schema):
    """Sample size result."""

    loss_value = fields.Float(
        metadata={'description': 'Expected loss of choosing B over A at '
                                 'this sample size.'})
    probability_B_over_A = fields.Float(
        metadata={'description': 'Probability that B beats A.'})
    sample_size_per_variant = fields.Int(
        metadata={'description': 'Required sample size for each variant.'})


class LossFunctionResponse(Schema):
    """Expected loss and win probability for each variant."""

    choose_variant_A = fields.Float(
        metadata={'description': 'Expected loss of choosing A.'})
    choose_variant_B = fields.Float(
        metadata={'description': 'Expected loss of choosing B.'})
    probability_A_greater_than_B = fields.Float(
        metadata={'description': 'Probability that A beats B.'})
    probability_B_greater_than_A = fields.Float(
        metadata={'description': 'Probability that B beats A.'})


class ErrorResponse(Schema):
    """Error body returned for any HTTP error."""

    response_code = fields.Int(
        metadata={'description': 'HTTP status code of the error.'})
    message = fields.Str(
        metadata={'description': 'Human readable summary of the error.'})
    errors = fields.Dict(
        required=False,
        metadata={'description': 'Validation messages keyed by the name of '
                                 'the offending parameter. Only present for '
                                 'invalid parameters.'})


def _operation(summary, query, response):
    """Describe a GET operation taking a query schema."""
    return {'get': {
        'summary': summary,
        'parameters': [{'in': 'query', 'schema': query}],
        'responses': {
            '200': {'description': 'The calculation result',
                    'content': {'application/json': {'schema': response}}},
            '400': {'description': 'A parameter is missing or invalid, or '
                                   'the result is out of range',
                    'content': {'application/json': {
                        'schema': 'ErrorResponse'}}},
        }}}


def _build_spec():
    """Build the OpenAPI spec for every v1 route."""
    spec = APISpec(title='AB Test Sample Size API', version='1.0.0',
                   openapi_version='3.0.3',
                   plugins=[MarshmallowPlugin()],
                   info={'description': 'Bayesian AB test sample size '
                                        'estimation.'})
    spec.components.schema('ErrorResponse', schema=ErrorResponse)
    spec.path('/api/v1/sample_size/', operations=_operation(
        'Estimate sample size per variant', SampleSizeQuery,
        SampleSizeResponse))
    spec.path('/api/v1/loss_function/', operations=_operation(
        'Expected loss and win probability for two beta posteriors',
        LossFunctionQuery, LossFunctionResponse))
    return spec.to_dict()


SPEC = _build_spec()

DOCS_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>AB Test Sample Size API</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js">
  </script>
  <script>SwaggerUIBundle({url: '/api/v1/', dom_id: '#swagger-ui',
                   defaultModelsExpandDepth: -1});</script>
</body>
</html>
"""


@bp.route('/api/v1/', methods=["GET"])
def get_openapi():
    """Return the OpenAPI spec."""
    return flask.jsonify(SPEC)


@bp.route('/api/docs', methods=["GET"])
def get_docs():
    """Render interactive API docs."""
    return DOCS_HTML
