from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme

from .views import MerchantsIndex

admin = Admin(
    name="Merchants",
    theme=Bootstrap4Theme(swatch="pulse", fluid=True),
    index_view=MerchantsIndex(url="/"),
)
