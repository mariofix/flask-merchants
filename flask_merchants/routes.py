from flask import Blueprint, render_template

blueprint = Blueprint("merchants", __name__)


@blueprint.get("/")
def merchants_home():
    return render_template("merchants/home.html")
