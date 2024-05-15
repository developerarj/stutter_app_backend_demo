# __init__.py

from flask import Flask
from flask_pymongo import PyMongo
from config import Config
from .routes.admin_routes import admin_bp, initialize_admin_routes
from .routes.user_routes import user_bp, initialize_user_routes
from .routes.common_routes import common_bp, initialize_common_routes
from .routes.static_routes import static_bp


def create_app(config_class=Config):
    app = Flask(__name__, static_url_path='', static_folder='files')
    app.config.from_object(config_class)

    mongo = PyMongo(app)

    mongo.init_app(app)

    with app.app_context():

        if 'users' not in mongo.db.list_collection_names():
            mongo.db.create_collection('users')

        if 'stutter_class_modal' not in mongo.db.list_collection_names():
            mongo.db.create_collection('stutter_class_modal')

        if 'modal' not in mongo.db.list_collection_names():
            mongo.db.create_collection('modal')

        if 'audioFiles' not in mongo.db.list_collection_names():
            mongo.db.create_collection('audioFiles')

        if 'classifications' not in mongo.db.list_collection_names():
            mongo.db.create_collection('classifications')

    initialize_admin_routes(mongo)
    initialize_user_routes(mongo)
    initialize_common_routes(mongo)

    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(common_bp)
    app.register_blueprint(static_bp)

    return app
