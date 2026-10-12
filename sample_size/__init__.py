"""
sample_size package initializer.

Baker Moran <bamoran99@gmail.com>
"""
import flask

from sample_size import api, web

# Uploads are read into memory
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def create_app(config=None):
    """Build the Flask app, with any `config` mapping applied over defaults."""
    app = flask.Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES
    if config:
        app.config.update(config)

    for blueprint in [*web.blueprints, *api.blueprints]:
        app.register_blueprint(blueprint)
    return app
