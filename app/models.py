# app/models.py

from app import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save(self):
        result = mongo.db.users.insert_one(self.to_dict())
        self.user_id = result.inserted_id  # Set the user's _id as user_id
        return result

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash
        }

    @staticmethod
    def get_all():
        return mongo.db.users.find()
