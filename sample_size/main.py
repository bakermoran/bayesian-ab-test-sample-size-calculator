"""main route."""
import flask
from marshmallow import Schema, ValidationError

from sample_size.api.v1.sample_size import (
    SAMPLE_SIZE_ARGS,
    _validate_variant_conversion_rate,
)
from sample_size.core.stats import (
    _frequentist_sample_size,
    _sample_size_fixed_loss_tolerance,
)

bp = flask.Blueprint('main', __name__)

SampleSizeSchema = Schema.from_dict(SAMPLE_SIZE_ARGS)


@bp.route('/', methods=["GET"])
def home_view():
    """Render the sample size form, and results when it has been submitted."""
    # Blank inputs mean "use the default"
    form = {k: v.strip() for k, v in flask.request.args.items() if v.strip()}
    context = {'form': form, 'errors': None, 'results': None}
    if form:
        try:
            args = SampleSizeSchema().load(form)
            _validate_variant_conversion_rate(args)
            results = _sample_size_fixed_loss_tolerance(**args)
            frequentist = _frequentist_sample_size(
                args['baseline_conversion_rate'],
                args['expected_relative_lift'], args['power'])
            results['frequentist_sample_size'] = frequentist
            results['sample_size_ratio'] = (
                results['sample_size_per_variant'] / frequentist)
            context['results'] = results
        except ValidationError as error:
            context['errors'] = error.messages
        except ValueError as error:
            context['errors'] = {'error': [str(error)]}
    return flask.render_template('index.html', **context)
