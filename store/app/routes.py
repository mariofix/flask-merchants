from flask import Blueprint, render_template

core_bp = Blueprint("core", __name__)


@core_bp.route("/", methods=["GET"])
def index():
    return render_template("seleccion.html")


@core_bp.route("/ayuda", methods=["GET"])
def ayuda():
    return render_template("core/ayuda.html")


@core_bp.route("/configuracion", methods=["GET"])
def configuracion():
    return render_template("core/configuracion.html")
