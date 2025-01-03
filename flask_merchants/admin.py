from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme

admin = Admin(name="Merchants", theme=Bootstrap4Theme(swatch="pulse", fluid=False))
