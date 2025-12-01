from flask import Blueprint, render_template

pos_bp = Blueprint("pos", __name__)


@pos_bp.route("/", methods=["GET"])
def index():
    return render_template("pos/dashboard.html")
