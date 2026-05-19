"""Flask-Admin views for managing payments stored by flask-merchants.

Install the optional dependency before using this module::

    pip install "flask-merchants[admin]"

Example - manual registration::

    from flask import Flask
    from flask_admin import Admin
    from flask_merchants import FlaskMerchants
    from flask_merchants.contrib.admin import PaymentView, ProvidersView

    app = Flask(__name__)
    ext = FlaskMerchants(app)

    admin = Admin(app, name="My Shop")
    admin.add_view(PaymentView(ext, name="Payments", endpoint="payments"))
    admin.add_view(ProvidersView(ext, name="Providers", endpoint="providers"))

Example - automatic registration (pass ``admin=`` to FlaskMerchants)::

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_admin import Admin
    from flask_merchants import FlaskMerchants
    from flask_merchants.models import PaymentMixin

    app = Flask(__name__)
    db = SQLAlchemy(model_class=Base)
    admin = Admin(app, name="My Shop")
    ext = FlaskMerchants(app, db=db, models=[MyPayment], admin=admin)
    # A PaymentModelView for MyPayment (SQLAlchemy-backed, with full column config)
    # and a ProvidersView are automatically added under category="Merchants".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from flask import flash

from flask_merchants.contrib.base import _STATUS_CHOICES, PaymentViewMixin

try:
    from flask_admin.actions import action
    from flask_admin.model import BaseModelView
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "flask-admin is required for flask_merchants.contrib.admin. "
        "Install it with: pip install 'flask-merchants[admin]'"
    ) from exc

if TYPE_CHECKING:
    from flask_merchants import FlaskMerchants


def _mask_secret(value: str) -> str:
    """Return *value* with all but the first 5 and last 1 characters masked.

    Short values (6 characters or fewer) are replaced entirely with ``"***"``
    to avoid leaking meaningful content through the masking pattern.

    Examples::

        _mask_secret("sk_test_1234567890")  # -> "sk_te…0"
        _mask_secret("short")               # -> "***"
    """
    if len(value) <= 6:
        return "***"
    return value[:5] + "…" + value[-1]


def _get_auth_info(auth) -> dict[str, str]:
    """Extract and mask auth details from an :class:`~merchants.auth.AuthStrategy`.

    Returns a dict with ``type``, ``header``, and ``masked_value`` keys.
    When *auth* is ``None`` an empty/unauthenticated descriptor is returned.
    """
    if auth is None:
        return {"type": "None", "header": "-", "masked_value": "-"}

    auth_type = type(auth).__name__
    # ApiKeyAuth stores the key in _api_key; TokenAuth in _token
    raw = getattr(auth, "_api_key", None) or getattr(auth, "_token", None) or ""
    header = getattr(auth, "_header", "-")
    return {
        "type": auth_type,
        "header": str(header),
        "masked_value": _mask_secret(raw) if raw else "-",
    }


def _extract_provider_base_url(provider) -> str:
    """Return the base URL from a provider using multiple fallback strategies.

    Different provider implementations store the base URL under different
    attribute names:

    * ``_base_url`` — used by Khipu, Stripe, PayPal, Dummy.
    * ``_client.api_url`` — used by Flow (pyflowcl ApiClient).
    * ``_checkout_url`` — used by GenericProvider.
    """
    url = (
        getattr(provider, "_base_url", None)
        or getattr(getattr(provider, "_client", None), "api_url", None)
        or getattr(provider, "_checkout_url", None)
    )
    return url or "N/A"


def _infer_provider_auth(provider) -> dict[str, str]:
    """Infer auth info from a provider that does not expose a standard ``_auth`` attribute.

    Handles the auth patterns used by providers that manage credentials
    internally rather than delegating to an :class:`~merchants.auth.AuthStrategy`:

    * Stripe/PayPal — store a raw key/token and build ``Authorization: Bearer …``
      headers in ``_headers()`` instead of using an ``AuthStrategy``.
    * Flow — uses HMAC-SHA256 signing via the pyflowcl ``ApiClient``.
    * GenericProvider — may supply custom headers via ``_extra_headers``.
    """
    # Standard AuthStrategy object (Khipu, anything that sets self._auth)
    auth = getattr(provider, "_auth", None)
    if auth is not None:
        return _get_auth_info(auth)

    # Stripe: self._api_key, no _client wrapper
    api_key = getattr(provider, "_api_key", None)
    if api_key and not hasattr(provider, "_client"):
        return {
            "type": "ApiKeyAuth",
            "header": "Authorization",
            "masked_value": _mask_secret(api_key),
        }

    # PayPal: self._access_token
    access_token = getattr(provider, "_access_token", None)
    if access_token:
        return {
            "type": "TokenAuth",
            "header": "Authorization",
            "masked_value": _mask_secret(access_token),
        }

    # Flow: pyflowcl ApiClient — HMAC-SHA256 via api_key + api_secret
    inner_client = getattr(provider, "_client", None)
    if inner_client is not None:
        inner_key = getattr(inner_client, "api_key", None) or getattr(inner_client, "_api_key", None)
        if inner_key:
            return {
                "type": "HmacAuth",
                "header": "X-Signature",
                "masked_value": _mask_secret(str(inner_key)),
            }

    # GenericProvider: extra_headers may carry auth-like headers
    extra = getattr(provider, "_extra_headers", None)
    if extra:
        auth_header = next(
            (k for k in extra if "auth" in k.lower() or "token" in k.lower() or "key" in k.lower()),
            next(iter(extra), None),
        )
        if auth_header:
            return {
                "type": "CustomHeader",
                "header": auth_header,
                "masked_value": _mask_secret(str(extra[auth_header])),
            }

    return {"type": "None", "header": "-", "masked_value": "-"}


class _PaymentRecord:
    """Placeholder model class used as the ``model`` argument for :class:`PaymentView`."""


class PaymentView(PaymentViewMixin, BaseModelView):
    """Flask-Admin view that lists all stored payments and allows managing them.

    Extends :class:`~flask_admin.model.BaseModelView` so the list page gains
    built-in search, column sorting, pagination, and actions consistent with
    other model-backed views in the admin.

    Provides:
    - List of all stored payment sessions with search and sorting.
    - Edit payment status via modal popup (one payment at a time).
    - Bulk Refund, Cancel, and Sync actions via the "With selected" action dropdown.

    Args:
        ext: Initialised :class:`~flask_merchants.FlaskMerchants` extension instance.
        name: Display name shown in the admin navigation bar.
        endpoint: Internal Flask endpoint prefix (must be unique).
        category: Optional admin category/group name.
    """

    # Disable create/delete; enable modal edit for payment-status changes.
    can_create = True
    can_delete = True
    can_edit = True
    can_view_details = True
    edit_modal = False

    # Column configuration (core columns + details/search/sort for in-memory backend)
    column_details_list: ClassVar[list] = [
        "merchants_id",
        "transaction_id",
        "provider",
        "amount",
        "currency",
        "payment_status",
    ]
    column_searchable_list: ClassVar[list] = ["merchants_id", "transaction_id", "provider", "payment_status"]
    column_sortable_list: ClassVar[list] = ["provider", "amount", "currency", "payment_status"]

    def __init__(
        self,
        ext: FlaskMerchants,
        name: str = "Payments",
        endpoint: str = "payments",
        category: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._ext = ext
        super().__init__(
            model=_PaymentRecord,
            name=name,
            endpoint=endpoint,
            category=category,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Required BaseModelView abstract methods
    # ------------------------------------------------------------------

    def scaffold_list_columns(self) -> list[str]:
        return ["merchants_id", "transaction_id", "provider", "amount", "currency", "payment_status"]

    def scaffold_sortable_columns(self) -> dict[str, str]:
        return {
            "provider": "provider",
            "amount": "amount",
            "currency": "currency",
            "payment_status": "payment_status",
        }

    def scaffold_form(self):
        from wtforms import Form as WTForm
        from wtforms import SelectField

        choices = _STATUS_CHOICES

        class StateForm(WTForm):
            payment_status = SelectField(
                "Payment Status",
                choices=choices,
                description="The current processing status of this payment session.",
            )

        return StateForm

    def scaffold_list_form(self, widget=None, validators=None):
        from wtforms import Form as WTForm

        return WTForm

    def init_search(self) -> bool:
        return bool(self.column_searchable_list)

    def _get_field_value(self, model, name):
        if isinstance(model, dict):
            return model.get(name)
        return super()._get_field_value(model, name)

    def get_pk_value(self, model) -> str | None:
        if isinstance(model, dict):
            return model.get("merchants_id")
        return getattr(model, "merchants_id", None)

    def get_list(self, page, sort_field, sort_desc, search, filters, page_size=None):
        payments = self._ext.all_sessions()

        if search:
            search_lower = search.lower()
            payments = [
                p
                for p in payments
                if search_lower in str(p.get("merchants_id", "")).lower()
                or search_lower in str(p.get("transaction_id", "")).lower()
                or search_lower in str(p.get("provider", "")).lower()
                or search_lower in str(p.get("payment_status", "")).lower()
            ]

        if sort_field:
            payments = sorted(
                payments,
                key=lambda p: str(p.get(sort_field, "")),
                reverse=bool(sort_desc),
            )

        count = len(payments)

        if page_size is None:
            page_size = self.page_size
        if page is not None and page_size:
            payments = payments[page * page_size : (page + 1) * page_size]

        return count, payments

    def get_one(self, id: str):
        return self._ext.get_session(id)

    def create_model(self, form):
        return False

    def update_model(self, form, model) -> bool:
        """Update payment status from the modal edit form."""
        payment_id = self.get_pk_value(model)
        new_status = form.payment_status.data
        if self._ext.update_payment_status(payment_id, new_status):
            flash(f"Payment {payment_id} updated to '{new_status}'.", "success")
            return True
        flash(f"Payment {payment_id} not found.", "danger")
        return False

    def delete_model(self, model):
        return False

    def get_empty_list_message(self) -> str:
        return "No payments recorded yet."

    # ------------------------------------------------------------------
    # Bulk actions - shown in the "With selected" dropdown
    # ------------------------------------------------------------------

    @action(
        "refund",
        "Refund",
        "Are you sure you want to mark the selected payments as refunded?",
    )
    def action_refund(self, ids: list[str]) -> None:
        """Mark selected payments as refunded."""
        count = sum(1 for pid in ids if self._ext.refund_session(pid))
        flash(f"{count} payment(s) marked as refunded.", "success")

    @action(
        "cancel",
        "Cancel",
        "Are you sure you want to cancel the selected payments?",
    )
    def action_cancel(self, ids: list[str]) -> None:
        """Cancel selected payments."""
        count = sum(1 for pid in ids if self._ext.cancel_session(pid))
        flash(f"{count} payment(s) cancelled.", "success")

    @action(
        "sync",
        "Sync from Provider",
        "Fetch live status from the provider for the selected payments?",
    )
    def action_sync(self, ids: list[str]) -> None:
        """Sync selected payments from their provider."""
        count = 0
        for pid in ids:
            if self._ext.sync_from_provider(pid) is not None:
                count += 1
        flash(f"{count} payment(s) synced from provider.", "success")


class _ProviderRecord:
    """Placeholder model class used as the ``model`` argument for :class:`ProvidersView`."""


class ProvidersView(BaseModelView):
    """Flask-Admin view that lists all payment providers registered with the application.

    Extends :class:`~flask_admin.model.BaseModelView` so the list page gains
    built-in search, column sorting, and pagination consistent with other
    model-backed views in the admin.

    Args:
        ext: Initialised :class:`~flask_merchants.FlaskMerchants` extension instance.
        name: Display name shown in the admin navigation bar.
        endpoint: Internal Flask endpoint prefix (must be unique).
        category: Optional admin category/group name.
    """

    # Providers are read-only in the admin.
    can_create = False
    can_edit = False
    can_delete = False

    # Column configuration
    column_list: ClassVar[list] = [
        "key",
        "base_url",
        "auth_type",
        "auth_header",
        "auth_masked_value",
        "transport",
        "payment_count",
    ]
    column_searchable_list: ClassVar[list] = ["key", "base_url", "auth_type"]
    column_sortable_list: ClassVar[list] = ["key", "payment_count"]
    column_labels: ClassVar[dict] = {
        "key": "Provider Key",
        "base_url": "Base URL",
        "auth_type": "Auth Type",
        "auth_header": "Auth Header",
        "auth_masked_value": "Auth Value",
        "transport": "Transport",
        "payment_count": "Payments",
    }
    column_descriptions: ClassVar[dict] = {
        "key": "Unique identifier used to reference this provider in the application.",
        "base_url": "Base API endpoint URL for this provider.",
        "auth_type": "Authentication strategy used for API requests (e.g. ApiKeyAuth, TokenAuth).",
        "auth_header": "HTTP header name used to send authentication credentials.",
        "auth_masked_value": "Masked authentication token (first 5 and last 1 characters shown).",
        "transport": "HTTP transport class used for provider API communication.",
        "payment_count": "Number of payment sessions recorded for this provider.",
    }

    # Custom list template - extends admin/model/list.html for consistent UI.
    list_template = "flask_merchants/admin/providers_list.html"

    def __init__(
        self,
        ext: FlaskMerchants,
        name: str = "Providers",
        endpoint: str = "providers",
        category: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._ext = ext
        super().__init__(
            model=_ProviderRecord,
            name=name,
            endpoint=endpoint,
            category=category,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Required BaseModelView abstract methods
    # ------------------------------------------------------------------

    def scaffold_list_columns(self) -> list[str]:
        return [
            "key",
            "base_url",
            "auth_type",
            "auth_header",
            "auth_masked_value",
            "transport",
            "payment_count",
        ]

    def scaffold_sortable_columns(self) -> dict[str, str]:
        return {"key": "key", "payment_count": "payment_count"}

    def scaffold_form(self):
        from wtforms import Form as WTForm

        return WTForm

    def scaffold_list_form(self, widget=None, validators=None):
        from wtforms import Form as WTForm

        return WTForm

    def init_search(self) -> bool:
        return bool(self.column_searchable_list)

    def get_pk_value(self, model) -> str | None:
        if isinstance(model, dict):
            return model.get("key")
        return getattr(model, "key", None)

    def _build_providers_list(self) -> list[dict]:
        """Build the enriched list of provider dicts from the merchants SDK."""
        import merchants as merchants_sdk

        provider_keys = merchants_sdk.list_providers()

        all_payments = self._ext.all_sessions()
        payment_counts: dict[str, int] = {}
        for p in all_payments:
            pkey = p.get("provider", "")
            payment_counts[pkey] = payment_counts.get(pkey, 0) + 1

        providers = []
        for key in provider_keys:
            try:
                client = self._ext.get_client(key)
                base_url = _extract_provider_base_url(client._provider)
                auth_info = _infer_provider_auth(client._provider)
                transport = type(client._transport).__name__
            except Exception:
                base_url = "N/A"
                auth_info = _get_auth_info(None)
                transport = "N/A"

            providers.append(
                {
                    "key": key,
                    "base_url": base_url,
                    "auth_type": auth_info["type"],
                    "auth_header": auth_info["header"],
                    "auth_masked_value": auth_info["masked_value"],
                    "transport": transport,
                    "payment_count": payment_counts.get(key, 0),
                }
            )

        return providers

    def get_list(self, page, sort_field, sort_desc, search, filters, page_size=None):
        providers = self._build_providers_list()

        if search:
            search_lower = search.lower()
            providers = [
                p
                for p in providers
                if search_lower in str(p.get("key", "")).lower()
                or search_lower in str(p.get("base_url", "")).lower()
                or search_lower in str(p.get("auth_type", "")).lower()
            ]

        if sort_field:
            providers = sorted(
                providers,
                key=lambda p: str(p.get(sort_field, "")),
                reverse=bool(sort_desc),
            )

        count = len(providers)

        if page_size is None:
            page_size = self.page_size
        if page is not None and page_size:
            providers = providers[page * page_size : (page + 1) * page_size]

        return count, providers

    def get_one(self, id: str):
        return next((p for p in self._build_providers_list() if p.get("key") == id), None)

    def create_model(self, form):
        return False

    def update_model(self, form, model):
        return False

    def delete_model(self, model):
        return False

    def get_empty_list_message(self) -> str:
        return "No providers registered."


def register_admin_views(
    admin,
    ext: FlaskMerchants,
    *,
    payment_name: str = "Payments",
    provider_name: str = "Providers",
    payment_json_fields: tuple[str, ...] | list[str] = (),
    payment_json_widget: str = "",
) -> None:
    """Register the standard Merchants admin views into *admin*.

    When a SQLAlchemy *db* was supplied to the extension a
    :class:`~flask_merchants.contrib.sqla.PaymentModelView` is registered for
    each payment model class — inheriting the full column configuration from
    :class:`~flask_merchants.contrib.base.PaymentViewMixin` (formatters,
    descriptions, labels, state choices).  When no *db* is configured the
    in-memory :class:`PaymentView` is used as a fallback.

    :class:`ProvidersView` is always registered under ``category="Merchants"``.

    Called automatically when you pass ``admin=`` to
    :class:`~flask_merchants.FlaskMerchants`::

        admin = Admin(app, name="My Shop")
        ext = FlaskMerchants(app, db=db, models=[Payment], admin=admin)
        # A PaymentModelView for Payment and a ProvidersView are added automatically.

    You can also call it manually if you need finer control::

        register_admin_views(admin, ext)

    When called via ``FlaskMerchants.init_app``, the *payment_name* and
    *provider_name* values are read from ``app.config`` using
    ``MERCHANTS_PAYMENT_VIEW_NAME`` and ``MERCHANTS_PROVIDER_VIEW_NAME``
    respectively.

    Args:
        admin: A :class:`flask_admin.Admin` instance.
        ext: An initialised :class:`~flask_merchants.FlaskMerchants` instance.
        payment_name: Display name for the Payments menu item.
        provider_name: Display name for the Providers menu item.
        payment_json_fields: Payment model fields that should render using
            the widget configured in *payment_json_widget*.
        payment_json_widget: Dotted import path to the widget class/object
            used for *payment_json_fields*.
    """
    if ext._db is not None:
        from flask_merchants.contrib.sqla import PaymentModelView

        for model_cls in ext._get_model_classes():
            endpoint = f"merchants_{model_cls.__tablename__}"
            admin.add_view(
                PaymentModelView(
                    model_cls,
                    ext._db.session,
                    ext=ext,
                    payment_json_fields=payment_json_fields,
                    payment_json_widget=payment_json_widget,
                    name=payment_name,
                    endpoint=endpoint,
                    category="Merchants",
                )
            )
    else:
        admin.add_view(
            PaymentView(
                ext,
                name=payment_name,
                endpoint="merchants_payments",
                category="Merchants",
            )
        )

    admin.add_view(
        ProvidersView(
            ext,
            name=provider_name,
            endpoint="merchants_providers",
            category="Merchants",
        )
    )
