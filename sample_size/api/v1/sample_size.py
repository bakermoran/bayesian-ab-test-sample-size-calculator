"""REST API for sample size calcs."""
import flask
from marshmallow import ValidationError
from webargs import fields, validate
from webargs.flaskparser import use_kwargs

from sample_size.core.stats import _sample_size_fixed_loss_tolerance

bp = flask.Blueprint('sample_size', __name__)

SAMPLE_SIZE_ARGS = {
    'baseline_conversion_rate': fields.Float(
        required=True,
        validate=validate.Range(min=0, max=1, min_inclusive=False,
                                max_inclusive=False),
        metadata={'description': 'Conversion rate of the control variant (A), '
                                 'as a fraction between 0 and 1.',
                  'example': 0.05}),
    'expected_relative_lift': fields.Float(
        required=True, validate=validate.Range(min=0, min_inclusive=False),
        metadata={'description': 'Relative lift you expect variant B to '
                                 'achieve over A, e.g. 0.1 for +10%.',
                  'example': 0.1}),
    'loss_tolerance': fields.Float(
        load_default=.002, validate=validate.Range(min=0, min_inclusive=False),
        metadata={'description': 'Largest expected loss, in conversion rate, '
                                 'you will accept when choosing the wrong '
                                 'variant.'}),
    'power': fields.Float(
        load_default=.8,
        validate=validate.Range(min=.5, max=1, max_inclusive=False),
        metadata={'description': 'Probability that the experiment reaches the '
                                 'loss tolerance when the expected lift is '
                                 'real.'}),
    'prior_alpha': fields.Int(
        load_default=1, validate=validate.Range(min=1),
        metadata={'description': 'Alpha (prior successes) of the Beta prior '
                                 'on each variant.'}),
    'prior_beta': fields.Int(
        load_default=1, validate=validate.Range(min=1),
        metadata={'description': 'Beta (prior failures) of the Beta prior on '
                                 'each variant.'}),
}


def _validate_variant_conversion_rate(args):
    """Reject lifts that push the variant conversion rate to 100% or more."""
    if args['baseline_conversion_rate'] * (
            1 + args['expected_relative_lift']) >= 1:
        raise ValidationError({'expected_relative_lift': [
            'baseline_conversion_rate * (1 + expected_relative_lift) must be '
            'less than 1']})


@bp.route('/api/v1/sample_size/', methods=["GET"])
@use_kwargs(SAMPLE_SIZE_ARGS, location='query', error_status_code=400,
            validate=_validate_variant_conversion_rate)
def get_sample_size(baseline_conversion_rate, expected_relative_lift,
                    loss_tolerance, power, prior_alpha, prior_beta):
    """Get sample size estimate for parameters."""
    try:
        results = _sample_size_fixed_loss_tolerance(
                         baseline_conversion_rate=baseline_conversion_rate,
                         expected_relative_lift=expected_relative_lift,
                         loss_tolerance=loss_tolerance,
                         power=power,
                         prior_alpha=prior_alpha,
                         prior_beta=prior_beta)
    except ValueError as error:
        flask.abort(400, str(error))

    return flask.jsonify(**results)
