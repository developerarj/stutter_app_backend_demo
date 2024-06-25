# __init__.py

from flask import Flask
from flask_pymongo import PyMongo
from config import Config
from .routes.admin_routes import admin_bp, initialize_admin_routes
from .routes.user_routes import user_bp, initialize_user_routes
from .routes.common_routes import common_bp, initialize_common_routes
from .routes.static_routes import static_bp
from .routes.index_routes import index_bp  # Import the index blueprint
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging


def create_app(config_class=Config):
    load_dotenv()
    # Set up logging
    # logging.basicConfig(level=logging.DEBUG)
    # logger = logging.getLogger(__name__)

    app = Flask(__name__, static_url_path='',
                static_folder='files', template_folder='templates')
    CORS(app)
    app.config.from_object(config_class)

    app.config['MONGO_URI'] = os.getenv('MONGO_URI')
    mongo = PyMongo(app)

    mongo.init_app(app)

    with app.app_context():
        if 'users' not in mongo.db.list_collection_names():
            mongo.db.create_collection('users')

        if 'modal' not in mongo.db.list_collection_names():
            mongo.db.create_collection('modal')

        if 'audioFiles' not in mongo.db.list_collection_names():
            mongo.db.create_collection('audioFiles')

        if 'classifications' not in mongo.db.list_collection_names():
            mongo.db.create_collection('classifications')

        if 'predictions' not in mongo.db.list_collection_names():
            mongo.db.create_collection('predictions')

        if 'feedback' not in mongo.db.list_collection_names():
            mongo.db.create_collection('feedback')

        if 'activity' not in mongo.db.list_collection_names():
            mongo.db.create_collection('activity')

        if 'activitySession' not in mongo.db.list_collection_names():
            mongo.db.create_collection('activitySession')

        if 'activityTheme' not in mongo.db.list_collection_names():
            mongo.db.create_collection('activityTheme')

        if 'dialogue' not in mongo.db.list_collection_names():
            mongo.db.create_collection('dialogue')

    initialize_admin_routes(mongo)
    initialize_user_routes(mongo)
    initialize_common_routes(mongo)

    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(common_bp)
    app.register_blueprint(static_bp)
    app.register_blueprint(index_bp)  # Register the index blueprint

    return app
