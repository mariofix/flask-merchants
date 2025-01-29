from flask import render_template
from flask.views import MethodView


class StorefrontController(MethodView):
    init_every_request = False

    def __init__(self):
        super().__init__()

    def get(self):
        return render_template("landing.html")
