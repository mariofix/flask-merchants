from flask import Blueprint, render_template


core_bp = Blueprint("core", __name__)


@core_bp.route("/", methods=["GET"])
def index():
    return render_template("site/index.j2")


@core_bp.route("/buscar", methods=["GET"])
def buscar():
    return render_template("site/resultados.html")


@core_bp.route("/admin", methods=["GET"])
def admin():
    return render_template("seleccion.html")


@core_bp.route("/aiuda", methods=["GET"])
def ayuda():
    return render_template("core/ayuda.html")


@core_bp.route("/configuracion", methods=["GET"])
def configuracion():
    return render_template("core/configuracion.html")
