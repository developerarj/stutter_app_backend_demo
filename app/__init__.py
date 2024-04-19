from flask import Flask
from flask_pymongo import PyMongo
from config import Config

mongo = PyMongo()

def create_app(config_class=Config):
    app = Flask(__name__,static_url_path='', static_folder='files')
    app.config.from_object(config_class)

    mongo.init_app(app)

    with app.app_context():
        if 'users' not in mongo.db.list_collection_names():
            mongo.db.create_collection('users')

        # Check if stutter_class_model collection exists, if not create it
        if 'stutter_class_model' not in mongo.db.list_collection_names():
            mongo.db.create_collection('stutter_class_model')

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
    