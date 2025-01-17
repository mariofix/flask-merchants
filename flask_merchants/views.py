from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView


class MerchantsIndex(AdminIndexView):
    @expose("/")
    def index(self):
        return self.render("dashboard.html")


class IntegrationAdmin(ModelView):
    name = "Integration"
    name_plural = "Integrations"


class PaymentAdmin(ModelView):
    name = "Payment"
    name_plural = "Payments"

    column_list = ["merchants_token", "integration_slug", "currency", "amount", "status", "creation"]
