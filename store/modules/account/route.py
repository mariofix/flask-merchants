from flask import Blueprint, jsonify, make_response

from .controller import AccountController

account_bp = Blueprint("account", __name__)
account_controller = AccountController()


@account_bp.route("/", methods=["GET"])
def index():
    """Example endpoint with simple greeting.
    ---
    tags:
      - Example API
    responses:
      200:
        description: A simple greeting
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                message:
                  type: string
                  example: "Hello World!"
    """
    result = account_controller.index()
    return make_response(jsonify(data=result))
