from flask import Flask
from flask_pymongo import PyMongo
from config import Config

mongo = PyMongo()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    mongo.init_app(app)

    with app.app_context():
        if 'users' not in mongo.db.list_collection_names():
            mongo.db.create_collection('users')

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
