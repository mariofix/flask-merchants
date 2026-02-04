from flask import Blueprint, render_template, jsonify
from .reader import registra_lectura

pos_bp = Blueprint("pos", __name__)


@pos_bp.route("/", methods=["GET"])
def index():
    return render_template("pos/dashboard.html")


@pos_bp.route("/venta", methods=["GET"])
def venta():
    return render_template("pos/venta.html")


@pos_bp.route("/casino", methods=["GET"])
def casino():
    return render_template("pos/casino.html")


@pos_bp.route("/reader", methods=["GET"])
def reader():
    return render_template("pos/reader.html")


@pos_bp.route("/new-reading/")
@pos_bp.route("/new-reading/<int:qr_data>")
def nueva_lectura(qr_data):
    registra_lectura(qr_data=qr_data)
    return jsonify(qr_data)
