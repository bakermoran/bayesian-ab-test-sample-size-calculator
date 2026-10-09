"""REST API for sample size calcs."""
import flask
from webargs import fields, validate
from webargs.flaskparser import use_kwargs

from sample_size.core.stats import _loss_choose_b_over_a, _probability_b_beats_a

bp = flask.Blueprint('loss_function', __name__)

LOSS_FUNCTION_ARGS = {
    'alpha_a': fields.Int(data_key='alpha_A', required=True,
                          validate=validate.Range(min=1),
                          metadata={'description': 'Alpha of the Beta posterior for '
                                   'variant A (successes + prior).'}),
    'beta_a': fields.Int(data_key='beta_A', required=True,
                          validate=validate.Range(min=1),
                          metadata={'description': 'Beta of the Beta posterior for '
                                   'variant A (failures + prior).'}),
    'alpha_b': fields.Int(data_key='alpha_B', required=True,
                          validate=validate.Range(min=1),
                          metadata={'description': 'Alpha of the Beta posterior for '
                                   'variant B (successes + prior).'}),
    'beta_b': fields.Int(data_key='beta_B', required=True,
                          validate=validate.Range(min=1),
                          metadata={'description': 'Beta of the Beta posterior for '
                                   'variant B (failures + prior).'}),
}


@bp.route('/api/v1/loss_function/', methods=["GET"])
@use_kwargs(LOSS_FUNCTION_ARGS, location='query', error_status_code=400)
def get_loss_function(alpha_a, beta_a, alpha_b, beta_b):
    """Get loss_function value for each variant."""
    results = {}
    results['choose_variant_A'] = _loss_choose_b_over_a(  # pylint: disable=arguments-out-of-order
                                                        alpha_b, beta_b,
                                                        alpha_a, beta_a)
    results['choose_variant_B'] = _loss_choose_b_over_a(alpha_a, beta_a,
                                                        alpha_b, beta_b)

    results['probability_A_greater_than_B'] = _probability_b_beats_a(  # pylint: disable=arguments-out-of-order
                                                                     alpha_b,
                                                                     beta_b,
                                                                     alpha_a,
                                                                     beta_a)
    results['probability_B_greater_than_A'] = _probability_b_beats_a(alpha_a,
                                                                     beta_a,
                                                                     alpha_b,
                                                                     beta_b)

    return flask.jsonify(**results)
