import json

from flask import current_app
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup
from wtforms import ValidationError, fields


class AppAdmin:
    form_widget_args = {
        "creation": {
            "readonly": True,
        },
        "last_update": {
            "readonly": True,
        },
    }
    page_size = 20
    can_create = True
    can_edit = True
    can_delete = True
    column_display_pk = True
    save_as = True
    save_as_continue = True
    can_export = True
    can_view_details = True
    can_set_page_size = True


class MerchantsIndex(AdminIndexView):
    @expose("/")
    def index(self):
        return self.render("dashboard.html")


class IntegrationAdmin(AppAdmin, ModelView):
    name = "Integration"
    name_plural = "Integrations"
    column_list = ["slug", "integration_class", "is_active"]

    form_overrides = {"config": fields.TextAreaField}
    form_widget_args = {"config": {"rows": 10, "style": "font-family: monospace;"}}

    def _integration_class_validator(form, field):
        allowed_integrations = current_app.config.get("ALLOWED_INTEGRATIONS", [])

        if not field.data:
            return

        if field.data not in allowed_integrations:
            raise ValidationError(
                f'Integration class "{field.data}" is not allowed. Must be one of: {", ".join(allowed_integrations)}'
            )

    form_args = {"integration_class": {"validators": [_integration_class_validator]}}

    def on_form_prefill(self, form, id):
        if form.config.data:
            form.config.data = json.dumps(form.config.data, indent=2)

    def on_model_change(self, form, model, is_created):
        if isinstance(form.config.data, str):
            try:
                model.config = json.loads(form.config.data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")

    column_formatters_detail = {
        "config": lambda view, context, model, name: Markup(
            f'<pre style="white-space: pre-wrap; font-family: monospace;">{json.dumps(model.config, indent=2) if model.config else "{}"}</pre>'
        )
    }

    def is_html_allowed(self, name):
        # Enable safe HTML rendering for specific fields
        return name in ["config"]


class PaymentAdmin(AppAdmin, ModelView):
    name = "Payment"
    name_plural = "Payments"

    column_list = ["merchants_token", "integration_slug", "currency", "amount", "status", "creation"]
