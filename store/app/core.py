from flask import Flask, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_security.core import Security
from flask_security.datastore import SQLAlchemyUserDatastore
from flask_admin import helpers as admin_helpers


from .extensions import babel, mail
from .extensions.admin import admin
from .celery import celery_init_app
from .database import db, migrations
from .model import *  # noqa: F403
from .version import __version__
from .apoderado.route import apoderado_bp
from .pos.routes import pos_bp
from .routes import core_bp
from .tasks import MyMailUtil
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

    # Celery
    celery_init_app(app)

    if app.debug:
        from flask_debugtoolbar import DebugToolbarExtension

        toolbar = DebugToolbarExtension()
        # toolbar.init_app(app)

    # Setup Flask-Security
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore, mail_util_cls=MyMailUtil)

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

    app.register_blueprint(core_bp)
    app.register_blueprint(apoderado_bp, url_prefix="/apoderado")
    app.register_blueprint(pos_bp, url_prefix="/pos")

    return app
