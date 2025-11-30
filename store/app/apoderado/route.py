from flask import Blueprint, render_template
from .controller import ApoderadoController


apoderado_bp = Blueprint("apoderado", __name__)
apoderado_controller = ApoderadoController()


@apoderado_bp.route("/", methods=["GET"])
def index():
    return render_template("apoderado/dashboard.html")


@apoderado_bp.route("/abonar", methods=["GET", "POST"])
def abonar():
    return render_template("apoderado/abono.html")


@apoderado_bp.route("/menu-casino", methods=["GET"])
def menu_casino():
    return render_template("apoderado/menu-casino.html")


@apoderado_bp.route("/kiosko", methods=["GET"])
def kiosko():
    return render_template("apoderado/kiosko.html")


@apoderado_bp.route("/ficha-alumno/<int:id>", methods=["GET"])
def ficha(id):
    return render_template("apoderado/ficha.html")


@apoderado_bp.route("/abonos", methods=["GET"])
def abonos():
    return render_template("apoderado/abonos.html")
