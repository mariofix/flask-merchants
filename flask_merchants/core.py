import enum
from typing import Any, Optional

from .admin import admin


class PaymentStatus(enum.Enum):
    created = "created"
    processing = "processing"
    declined = "declined"
    cancelled = "cancelled"
    refunded = "refunded"
    paid = "paid"


class MerchantsError(Exception):
    pass


def get_model(db, model_name):
    for model in db.Model.__subclasses__():
        if model.__name__ == model_name:
            return model
    return None


def get_payment_model(current_app: Optional[Any] = None, sqla: Optional[Any] = None):
    model_config = current_app.config.get("PAYMENT_MODEL", None)

    try:
        return get_model(sqla, model_config.rsplit(".", 1).pop())
    except Exception:
        raise MerchantsError(f"Can't find PAYMENT_MODEL={model_config}")


def get_integration_model(current_app: Optional[Any] = None, sqla: Optional[Any] = None):
    model_config = current_app.config.get("INTEGRATION_MODEL", None)

    try:
        return get_model(sqla, model_config.rsplit(".", 1).pop())
    except Exception:
        raise MerchantsError(f"Can't find INTEGRATION_MODEL={model_config}")


class FlaskMerchants:
    app: Optional[Any]
    payment_model: Optional[Any]
    integration_model: Optional[Any]

    def __init__(self, app: Optional[Any] = None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        if hasattr(app, "extensions") and "flask_merchants" not in app.extensions:
            app.extensions["flask_merchants"] = self
        self.app = app

        # We need flask_sqlalchemy
        try:
            self.db = self.app.extensions["sqlalchemy"]
        except KeyError:
            raise MerchantsError(
                "Can't find 'sqlalchemy' in flask's extensions, please load merchants after flask_sqlalchemy"
            )

        # Check basic config stuff
        self.crosscheck()

        # Start
        self.start_merchants()

    def start_merchants(self):
        # Flask-Admin
        admin.init_app(self.app)

        # Get core models
        self.payment_model = get_payment_model(self.app, self.db)
        self.integration_model = get_integration_model(self.app, self.db)

        # Register ModelViews
        self.register_modelsviews()

    def crosscheck(self):
        if "PAYMENT_MODEL" not in self.app.config:
            raise MerchantsError("Please set up PAYMENT_MODEL= in your settings file or FLASK_PAYMENT_MODEL= env var.")
        if "INTEGRATION_MODEL" not in self.app.config:
            raise MerchantsError(
                "Please set up INTEGRATION_MODEL= in your settings file or FLASK_INTEGRATION_MODEL= env var."
            )

    def register_modelsviews(self):
        pass
