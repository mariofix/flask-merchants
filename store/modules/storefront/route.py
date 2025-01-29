from flask import Blueprint

from .controller import StorefrontController

storefront_bp = Blueprint(
    "storefront", __name__, static_folder="static", static_url_path="/store/static", template_folder="templates"
)

storefront_bp.add_url_rule("/", view_func=StorefrontController.as_view("landing"), endpoint="landing")
