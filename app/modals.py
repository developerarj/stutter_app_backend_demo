# app/modals.py

from app import mongo
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime

class User:
    def __init__(self, username, email, password, isAdmin=False):
        self.username = username
        self.email = email
        self.isAdmin = isAdmin
        self.createdDate = datetime.utcnow()
        self.updatedDate = datetime.utcnow()
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
            "password_hash": self.password_hash,
            "isAdmin": self.isAdmin,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }

    
class Modal:
    def __init__(self, modal_type, accuracy,url):
        self.type = modal_type
        self.accuracy = accuracy
        self.url=url
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.modal_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "type": self.type,
            "accuracy": self.accuracy,
            "url":self.url,
            "createdDate":self.createdDate,
            "updatedDate":self.updatedDate
        }
    

class AudioFiles:
    def __init__(self, user_id, url):
        self.user_id = user_id
        self.url = url
        self.createdDate = datetime.utcnow()
        self.updatedDate = datetime.utcnow()

    def save(self):
        result = mongo.db.audioFiles.insert_one(self.to_dict())
        self.audio_file_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "url": self.url,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }

    @staticmethod
    def get_all():
        return mongo.db.modal.find()
