from typing import Optional

from flask import Flask, request, session  # , url_for
from flask_babel import Babel
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.middleware.proxy_fix import ProxyFix

from flask_merchants.core import FlaskMerchants

from .database import db, migrations

merchants = FlaskMerchants()
toolbar = DebugToolbarExtension()


def create_app(settings_file: Optional[str] = None):
    app = Flask("Store", template_folder="store/templates")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Configure App, env takes precedence
    if settings_file:
        app.config.from_object(settings_file)
    app.config.from_prefixed_env()

    # SQLAlchemy&Flask-Migrate
    db.init_app(app)
    migrations.init_app(app, db, directory="store/migrations")

    # Flask-Merchants
    merchants.init_app(app)

    # Flask-Admin
    # admin.init_app(app, endpoint="merchants_old")
    # admin.add_view(PaymentAdmin(Payment, db.session))
    # admin.add_view(IntegrationAdmin(Integration, db.session))
    # admin.add_view(StoreFront())
    # admin.add_view(StoreProductView())
    # admin.add_view(StoreCheckoutView())

    # Flask-DebugToolbar
    # toolbar.init_app(app)

    # Flask-babel
    babel = Babel()

    def get_locale():
        if request.args.get("lang"):
            session["lang"] = request.args.get("lang")
        return session.get("lang", app.config.get("BABEL_DEFAULT_LOCALE"))

    def get_timezone():
        return app.config.get("BABEL_DEFAULT_TIMEZONE")

    babel.init_app(
        app,
        locale_selector=get_locale,
        timezone_selector=get_timezone,
        default_domain=app.config.get("BABEL_DOMAIN", "merchants"),
        default_translation_directories=app.config.get("BABEL_DEFAULT_FOLDER", "store/translations"),
    )
    app.logger.info(f"{app.extensions = }")

    return app
