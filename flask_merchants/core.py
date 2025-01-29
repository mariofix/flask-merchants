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
        if model and model.__name__ == model_name:
            return model
    return None


def get_payment_model(current_app: Optional[Any] = None, sqla: Optional[Any] = None):
    model_config = current_app.config.get("MERCHANTS_PAYMENT_MODEL", None)

    try:
        return get_model(sqla, model_config.rsplit(".", 1).pop())
    except Exception:
        raise MerchantsError(f"Can't find MERCHANTS_PAYMENT_MODEL={model_config}")


def get_integration_model(current_app: Optional[Any] = None, sqla: Optional[Any] = None):
    model_config = current_app.config.get("MERCHANTS_INTEGRATION_MODEL", None)

    try:
        return get_model(sqla, model_config.rsplit(".", 1).pop())
    except Exception:
        raise MerchantsError(f"Can't find MERCHANTS_INTEGRATION_MODEL={model_config}")


class FlaskMerchantsExtension:
    app: Optional[Any]
    payment_model: Optional[Any]
    integration_model: Optional[Any]

    def __init__(self, app: Optional[Any] = None, db: Optional[Any] = None):
        if app:
            self.init_app(app, db)

    def init_app(self, app, db=None):
        if hasattr(app, "extensions") and "flask_merchants" not in app.extensions:
            app.extensions["flask_merchants"] = self
        self.app = app

        # We need flask_sqlalchemy
        self.db = db

        # Check basic config stuff
        self.crosscheck()

        # Start
        self.start_merchants()

    def start_merchants(self):
        # Flask-Admin
        admin.init_app(self.app)

        # Register ModelViews
        self.register_modelsviews()

    def crosscheck(self):
        if "MERCHANTS_PAYMENT_MODEL" not in self.app.config:
            raise MerchantsError(
                "Please set up MERCHANTS_PAYMENT_MODEL:str in your settings file or FLASK_MERCHANTS_PAYMENT_MODEL env var."
            )
        self.payment_model = self.app.config["MERCHANTS_PAYMENT_MODEL"]

        if "MERCHANTS_INTEGRATION_MODEL" not in self.app.config:
            raise MerchantsError(
                "Please set up MERCHANTS_INTEGRATION_MODEL:str in your settings file or FLASK_MERCHANTS_INTEGRATION_MODEL env var."
            )
        self.integration_model = self.app.config["MERCHANTS_INTEGRATION_MODEL"]

    def register_modelsviews(self):
        from .views import IntegrationAdmin, PaymentAdmin

        admin.add_view(
            PaymentAdmin(
                get_model(self.db, self.payment_model.rsplit(".", 1).pop()),
                self.db.session,
                category="Merchants",
            ),
        )
        admin.add_view(
            IntegrationAdmin(
                get_model(self.db, self.integration_model.rsplit(".", 1).pop()),
                self.db.session,
                category="Merchants",
            ),
        )

    def add_admin_model(self, model, modelview):
        try:
            admin.add_view(
                modelview(
                    model,
                    self.db.session,
                ),
            )
        except Exception as e:
            self.app.logger.warn(f"{e}")
            raise e
