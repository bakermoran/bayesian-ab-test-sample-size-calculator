"""main route."""
import flask

bp = flask.Blueprint('main', __name__)


@bp.route('/', methods=["GET"])
def home_view():
    """Return home route."""
    url_root = flask.request.url_root
    return f'for the api, head to <a href="{url_root}api/v1">{url_root}</a>'
