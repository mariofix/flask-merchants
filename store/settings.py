from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY: str
DEBUG = True
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
TRUSTED_HOSTS = ["tardis.local"]
SESSION_COOKIE_NAME = "merchants"
ADMIN_BASE_URL = "admin"
SQLALCHEMY_DATABASE_URI = ""
SQLALCHEMY_RECORD_QUERIES = DEBUG
SQLALCHEMY_ECHO = False
SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 1800}

SECURITY_EMAIL_SENDER = "Merchants"
SECURITY_PASSWORD_SALT: str
SECURITY_LOGIN_URL = "/login/"
SECURITY_LOGOUT_URL = "/logout/"
SECURITY_POST_LOGIN_VIEW = "/"
SECURITY_POST_LOGOUT_VIEW = "/"
SECURITY_USERNAME_ENABLE = True
SECURITY_USERNAME_REQUIRED = True

# Flask-Babel
BABEL_DEFAULT_LOCALE = "en"
BABEL_DEFAULT_TIMEZONE = "UTC"
BABEL_DEFAULT_FOLDER = "store/translations"
BABEL_DOMAIN = "merchants"
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "es": {"flag": "mx", "name": "Español"},
}

# Flask Debugtoolbar
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = DEBUG
DEBUG_TB_PANELS = (
    "flask_debugtoolbar.panels.versions.VersionDebugPanel",
    "flask_debugtoolbar.panels.timer.TimerDebugPanel",
    "flask_debugtoolbar.panels.headers.HeaderDebugPanel",
    "flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel",
    "flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel",
    "flask_debugtoolbar.panels.template.TemplateDebugPanel",
    "flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel",
    "flask_debugtoolbar.panels.logger.LoggingPanel",
    "flask_debugtoolbar.panels.route_list.RouteListDebugPanel",
    "flask_debugtoolbar.panels.profiler.ProfilerDebugPanel",
    "flask_debugtoolbar.panels.g.GDebugPanel",
)
TEMPLATES_AUTO_RELOAD = True
EXPLAIN_TEMPLATE_LOADING = False


# Flask-Mailman
MAIL_SERVER = ""
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = ""
MAIL_PASSWORD = ""
MAIL_TIMEOUT = 5
MAIL_USE_LOCALTIME = True

ALLOWED_INTEGRATIONS = [
    "merchants.integrations.DummyProvider",
    "merchants.integrations.CashProvider",
]
PAYMENT_MODEL = "model.store.Payment"
INTEGRATION_MODEL = "model.store.Integration"
