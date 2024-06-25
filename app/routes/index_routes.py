# index_routes.py

from flask import Blueprint, render_template, jsonify

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def index():
    return jsonify({"data": 'Welcome to Stuttur App'}), 200
