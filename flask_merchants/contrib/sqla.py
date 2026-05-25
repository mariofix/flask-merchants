"""Flask-Admin ModelView for the SQLAlchemy-backed Payment model.

Requires the ``db`` extra::

    pip install "flask-merchants[db]"

Example::

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_admin import Admin
    from flask_merchants import FlaskMerchants
    from flask_merchants.models import PaymentMixin
    from flask_merchants.contrib.sqla import PaymentModelView

    db = SQLAlchemy(model_class=Base)

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///payments.db"
    app.config["SECRET_KEY"] = "change-me"

    ext = FlaskMerchants(app, db=db, models=[MyPayment])
    db.init_app(app)

    admin = Admin(app, name="My Shop")
    admin.add_view(PaymentModelView(MyPayment, db.session, ext=ext, name="Payments"))

    with app.app_context():
        db.create_all()
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, ClassVar

from flask_merchants.contrib.base import _STATUS_CHOICES, PaymentViewMixin, _fmt_payment_status

try:
    from flask_admin.actions import action
    from flask_admin.contrib.sqla import ModelView
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "flask-admin and flask-sqlalchemy are required for "
        "flask_merchants.contrib.sqla. "
        "Install them with: pip install 'flask-merchants[db]'"
    ) from exc

if TYPE_CHECKING:
    from flask_merchants import FlaskMerchants


def _load_widget_from_path(path: str) -> Any:
    """Import and return a WTForms widget from a dotted path.

    Examples:
        ``wtforms.widgets.TextArea`` -> ``TextArea()``
        ``myapp.widgets.json_widget`` -> object returned by that attribute
    """
    module_path, sep, attr_name = path.rpartition(".")
    if not sep or not module_path or not attr_name:
        raise ValueError(f"Invalid widget path {path!r}. Expected dotted path like 'package.module.WidgetClass'.")
    module = import_module(module_path)
    attr = getattr(module, attr_name)
    return attr() if isinstance(attr, type) else attr


class PaymentModelView(PaymentViewMixin, ModelView):
    """Flask-Admin view for the :class:`~flask_merchants.models.Payment` model.

    Provides:
    - Searchable / filterable list of all payment records.
    - Create, view, and edit payment records (all user-editable fields).
    - Payment status validation via ``on_model_change`` as a Flask-Admin-level guard,
      backed by the SQLAlchemy ``@validates`` hook in
      :class:`~flask_merchants.models.PaymentMixin` at the ORM level.
    - Bulk **Refund**, **Cancel**, and **Sync from Provider** actions.

    Args:
        model: The :class:`~flask_merchants.models.Payment` model class.
        session: A SQLAlchemy scoped session (e.g. ``db.session``).
        ext: Optional :class:`~flask_merchants.FlaskMerchants` instance.
            Required only for the *Sync from Provider* action.
        payment_json_fields: Optional list/tuple of field names that should use
            the JSON widget loaded from *payment_json_widget*.
        payment_json_widget: Optional dotted import path to a widget class/object
            (for example ``"wtforms.widgets.TextArea"``).
        name: Display name shown in the admin navigation bar.
        endpoint: Internal Flask endpoint prefix (must be unique).
        category: Optional admin category/group name.
    """

    # ------------------------------------------------------------------
    # Column configuration
    # ------------------------------------------------------------------
    # Extend the base 5 columns from PaymentViewMixin with timestamp columns.
    column_list: ClassVar[list] = [
        "merchants_id",
        "transaction_id",
        "provider",
        "amount",
        "currency",
        "payment_status",
        "created_at",
        "updated_at",
    ]
    column_labels: ClassVar[dict] = {
        **PaymentViewMixin.column_labels,
        "payment_status": "State",
        "created_at": "Created",
        "updated_at": "Updated",
    }
    column_descriptions: ClassVar[dict] = {
        **PaymentViewMixin.column_descriptions,
        "payment_status": "Current processing state of the payment.",
        "created_at": "Timestamp when this payment record was first created.",
        "updated_at": "Timestamp of the most recent update to this payment record.",
    }
    column_formatters: ClassVar[dict] = {
        **PaymentViewMixin.column_formatters,
        "payment_status": _fmt_payment_status,
    }
    column_searchable_list: ClassVar[list] = ["merchants_id", "transaction_id", "provider"]
    column_filters: ClassVar[list] = ["payment_status", "provider", "currency"]
    column_default_sort = ("created_at", True)
    can_view_details = True

    # Allow creating new payment records from the admin UI.
    can_create = True

    # Fields available when creating a new payment.
    form_create_columns: ClassVar[list] = [
        "merchants_id",
        "transaction_id",
        "provider",
        "amount",
        "currency",
        "payment_status",
    ]

    # Fields available when editing an existing payment.
    form_edit_columns: ClassVar[list] = [
        "provider",
        "amount",
        "currency",
        "payment_status",
    ]
    form_choices: ClassVar[dict] = {"payment_status": _STATUS_CHOICES}

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(
        self,
        model,
        session,
        *,
        ext: FlaskMerchants | None = None,
        payment_json_fields: tuple[str, ...] | list[str] | None = None,
        payment_json_widget: str = "",
        can_create: bool | None = None,
        can_edit: bool | None = None,
        can_delete: bool | None = None,
        **kwargs: Any,
    ) -> None:
        self._ext = ext
        self._payment_json_fields = tuple(str(f) for f in (payment_json_fields or ()))
        self._payment_json_widget = _load_widget_from_path(payment_json_widget) if payment_json_widget else None
        # Allow per-instance overrides of the class-level capability flags so
        # callers can restrict the UI without having to subclass:
        #
        #   PaymentModelView(Payment, db.session, ext=ext, can_create=False)
        if can_create is not None:
            self.can_create = can_create
        if can_edit is not None:
            self.can_edit = can_edit
        if can_delete is not None:
            self.can_delete = can_delete
        super().__init__(model, session, **kwargs)

    def scaffold_form(self):
        """Build the WTForms class and apply configured JSON widget overrides."""
        form_class = super().scaffold_form()
        if not self._payment_json_fields or self._payment_json_widget is None:
            return form_class
        for field_name in self._payment_json_fields:
            unbound_field = getattr(form_class, field_name, None)
            if unbound_field is None:
                continue
            unbound_field.kwargs["widget"] = self._payment_json_widget
        return form_class

    # ------------------------------------------------------------------
    # on_model_change hook
    # ------------------------------------------------------------------

    def on_model_change(self, form, model, is_created: bool) -> None:
        """Validate payment status before committing.

        WTForms rejects unknown choices via ``form_choices`` before this hook
        runs.  ``PaymentMixin.validate_payment_status`` (a SQLAlchemy ``@validates``
        hook) rejects invalid values at the ORM attribute level.  This method
        acts as a third, Flask-Admin-level guard so that any value that
        somehow slips through still raises a :class:`wtforms.ValidationError`
        and surfaces a clean error in the admin UI rather than an unhandled
        exception.
        """
        valid_statuses = {s for s, _ in _STATUS_CHOICES}
        if model.payment_status not in valid_statuses:
            from wtforms import ValidationError

            raise ValidationError(
                f"Invalid payment_status {model.payment_status!r}. Choose one of: {', '.join(sorted(valid_statuses))}."
            )

    def after_model_change(self, form, model, is_created: bool) -> None:
        """Called after a successful commit.

        Syncs the in-memory store (if the extension is available) so that
        both storage backends stay consistent.
        """
        if self._ext is not None:
            self._ext.update_payment_status(model.merchants_id, model.payment_status)

    # ------------------------------------------------------------------
    # Bulk actions
    # ------------------------------------------------------------------

    @action("refund", "Refund", "Mark selected payments as refunded?")
    def action_refund(self, ids: list[str]) -> None:
        """Mark the selected payment rows as *refunded*."""
        from flask import flash

        try:
            count = 0
            for pk in ids:
                record = self.get_one(pk)
                if record is not None:
                    record.payment_status = "refunded"
                    if self._ext is not None:
                        self._ext.update_payment_status(record.merchants_id, "refunded")
                    count += 1
            self.session.commit()
            flash(f"{count} payment(s) marked as refunded.", "success")
        except Exception as exc:
            self.session.rollback()
            flash(f"Failed to refund payments: {exc}", "danger")

    @action("cancel", "Cancel", "Cancel the selected payments?")
    def action_cancel(self, ids: list[str]) -> None:
        """Mark the selected payment rows as *cancelled*."""
        from flask import flash

        try:
            count = 0
            for pk in ids:
                record = self.get_one(pk)
                if record is not None:
                    record.payment_status = "cancelled"
                    if self._ext is not None:
                        self._ext.update_payment_status(record.merchants_id, "cancelled")
                    count += 1
            self.session.commit()
            flash(f"{count} payment(s) cancelled.", "success")
        except Exception as exc:
            self.session.rollback()
            flash(f"Failed to cancel payments: {exc}", "danger")

    @action("sync", "Sync from Provider", "Sync selected payments from the payment provider?")
    def action_sync(self, ids: list[str]) -> None:
        """Fetch live payment status from the provider and update each record."""
        from flask import flash

        if self._ext is None:
            flash("FlaskMerchants extension not configured; cannot sync.", "danger")
            return

        try:
            count = 0
            for pk in ids:
                record = self.get_one(pk)
                if record is None:
                    continue
                try:
                    status = self._ext.client.payments.get(record.transaction_id)
                    record.payment_status = status.state.value
                    count += 1
                except Exception:
                    pass
            self.session.commit()
            flash(f"{count} payment(s) synced from provider.", "success")
        except Exception as exc:
            self.session.rollback()
            flash(f"Failed to sync payments: {exc}", "danger")
