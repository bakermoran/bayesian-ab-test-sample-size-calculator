"""REST API for sample size calcs."""
import flask
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import BadRequest

from sample_size.core.sample_size import InputError, estimate_sample_size
from sample_size.schemas import SAMPLE_SIZE_ARGS

bp = flask.Blueprint('sample_size', __name__)


@bp.route('/api/v1/sample_size/', methods=["GET"])
@use_kwargs(SAMPLE_SIZE_ARGS, location='query', error_status_code=400)
def get_sample_size(**args):
    """Get sample size estimate for parameters."""
    try:
        results = estimate_sample_size(**args)
    except InputError as error:
        # Same shape as webargs validation failures, see handle_http_error
        bad_request = BadRequest(str(error))
        bad_request.data = {'messages': {error.field: [str(error)]}}
        raise bad_request from error
    except ValueError as error:
        flask.abort(400, str(error))

    return flask.jsonify(**results)
