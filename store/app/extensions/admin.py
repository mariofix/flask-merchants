from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from ..database import db
from ..model import Branch, BranchProduct, Category, Operador, Product, ProductType, Role, Settings, User, lecturas

admin = Admin(name="Merchants Store", url="/data-manager")


admin.add_view(ModelView(Product, db.session, category="Store"))
admin.add_view(ModelView(ProductType, db.session, category="Store"))
admin.add_view(ModelView(Category, db.session, category="Store"))

admin.add_view(ModelView(User, db.session, category="Users and Roles", name="Users"))
admin.add_view(ModelView(Role, db.session, category="Users and Roles", name="Roles"))
admin.add_view(ModelView(Operador, db.session, category="Users and Roles", name="Operadores"))
admin.add_view(ModelView(lecturas, db.session, category="Users and Roles", name="Lecturas"))

admin.add_view(ModelView(Branch, db.session, name="Branches", category="Settings"))
admin.add_view(ModelView(BranchProduct, db.session, name="Branch Product", category="Settings"))
admin.add_view(ModelView(Settings, db.session, name="Settings", category="Settings"))
