"""Shared error handling for the v1 REST API."""
import flask
from werkzeug.exceptions import HTTPException

bp = flask.Blueprint('v1', __name__)


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
