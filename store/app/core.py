from flask import Flask, render_template, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_security.core import Security
from flask_security.datastore import SQLAlchemyUserDatastore
from flask_admin import helpers as admin_helpers


from .extensions import babel, mail
from .extensions.admin import admin
from .database import db, migrations
from .model import *  # noqa: F403
from .version import __version__
import os
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask("Merchants_Store", template_folder="app/templates", static_folder="app/static")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Configure App, env takes precedence
    settings_file = os.getenv("FLASK_APP_SETTINGS_FILE", None)
    if settings_file:
        app.config.from_object(settings_file)
    app.config.from_prefixed_env()

    # Database Stuff
    babel.init_app(app)
    db.init_app(app)
    migrations.init_app(app, db, directory="app/migrations")
    admin.init_app(app)

    if app.debug:
        from flask_debugtoolbar import DebugToolbarExtension

        toolbar = DebugToolbarExtension()
        # toolbar.init_app(app)

    # Setup Flask-Security
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)

    # Flask-Mailman
    mail.init_app(app)

    @security.context_processor
    def security_context_processor():
        return dict(
            admin_base_template=admin.theme.base_template,
            admin_view=admin.index_view,
            theme=admin.theme,
            h=admin_helpers,
            get_url=url_for,
        )

    @app.context_processor
    def default_data():
        return {
            "app_version": __version__,
        }

    @app.get("/")
    def storefront():
        return render_template("store/dashboard.html")

    @app.get("/abonar")
    def abonar():
        return render_template("store/abono.html")

    @app.get("/ayuda")
    def ayuda():
        return render_template("store/ayuda.html")

    @app.get("/configuracion")
    def configuracion():
        return render_template("store/configuracion.html")

    return app
