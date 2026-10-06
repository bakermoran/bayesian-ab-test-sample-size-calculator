"""
sample_size package initializer.

Baker Moran <bamoran99@gmail.com>
"""
import flask
from flask_cors import CORS

from sample_size import api, main

# Routes live in blueprints; register them all on the single app object
app = flask.Flask(__name__)
CORS(app)

app.register_blueprint(main.bp)
for blueprint in api.blueprints:
    app.register_blueprint(blueprint)
