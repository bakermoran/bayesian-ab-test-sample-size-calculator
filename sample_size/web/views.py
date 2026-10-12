"""HTML views."""
import base64

import flask
from marshmallow import Schema, ValidationError
from werkzeug.exceptions import RequestEntityTooLarge

from sample_size.core import analysis
from sample_size.core.sample_size import InputError, estimate_sample_size
from sample_size.schemas import SAMPLE_SIZE_ARGS

bp = flask.Blueprint('web', __name__)

SampleSizeSchema = Schema.from_dict(SAMPLE_SIZE_ARGS)


@bp.route('/', methods=["GET"])
def home():
    """Render the landing page."""
    return flask.render_template('index.html')


@bp.route('/sample_size/', methods=["GET"])
def sample_size_view():
    """Render the sample size form, and results when it has been submitted."""
    # Blank inputs mean "use the default"
    form = {k: v.strip() for k, v in flask.request.args.items() if v.strip()}
    context = {'form': form, 'errors': None, 'results': None}
    if form:
        try:
            args = SampleSizeSchema().load(form)
            context['results'] = estimate_sample_size(**args)
        except ValidationError as error:
            context['errors'] = error.messages
        except InputError as error:
            context['errors'] = {error.field: [str(error)]}
        except ValueError as error:
            context['errors'] = {'error': [str(error)]}
    return flask.render_template('sample_size/index.html', **context)


def _analyze_page(status=200, **context):
    """Render the upload page, with the form values and any outcome."""
    context.setdefault('form', {})
    context.setdefault('errors', None)
    context.setdefault('results', None)
    context['families'] = analysis.FAMILIES
    return flask.render_template('analyze/index.html', **context), status


@bp.route('/analyze/', methods=["GET", "POST"])
def analyze():
    """Render the upload form, and analyze the uploaded CSV on submit.

    The file is parsed from the request stream in memory and never saved.
    """
    if flask.request.method == 'GET':
        return _analyze_page()

    form = {k: v.strip() for k, v in flask.request.form.items()}
    upload = flask.request.files.get('file')
    if upload is None or not upload.filename:
        return _analyze_page(400, form=form,
                             errors={'file': ['Choose a CSV file']})
    if not form.get('metric'):
        return _analyze_page(400, form=form,
                             errors={'metric': ['Enter the metric column']})
    try:
        results = analysis.analyze_csv(
            upload.stream, form['metric'], form.get('family', 'beta'),
            group=form.get('group') or 'bucket',
            control=form.get('control') or 'off',
            prior=form.get('prior', 'empirical'))
    except analysis.Busy as error:
        return _analyze_page(503, form=form, errors={'error': [str(error)]})
    except ValueError as error:
        return _analyze_page(400, form=form, errors={'error': [str(error)]})
    results['png'] = base64.b64encode(results['png']).decode('ascii')
    return _analyze_page(form=form, results=results)


@bp.errorhandler(RequestEntityTooLarge)
def upload_too_large(_error):
    """Show an upload over the size limit on the form, not as bare JSON."""
    limit = flask.current_app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)
    return _analyze_page(413, errors={'file': [f'File is over {limit} MB']})
