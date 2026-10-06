"""REST API for v1."""
import flask
from werkzeug.exceptions import HTTPException

bp = flask.Blueprint('v1', __name__)


@bp.route('/api/v1/', methods=["GET"])
def get_v1():
    """Return list of services available."""
    context = {}
    context['available_services'] = {'sample_size': '/api/v1/sample_size',
                                     'loss_function': '/api/v1/loss_function'}
    return flask.jsonify(**context)


@bp.app_errorhandler(HTTPException)
def handle_http_error(e):
    """Return HTTP errors as JSON, including webargs validation messages."""
    context = {}
    context['response_code'] = e.code
    context['message'] = e.description
    messages = getattr(e, 'data', {}).get('messages')
    if messages:
        context['message'] = 'Invalid request parameters.'
        context['errors'] = messages.get('query', messages)
    return flask.jsonify(**context), e.code
