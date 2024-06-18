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
    def __init__(self, modal_type: str, accuracy: float, url: str, isActive: bool, version: str):
        self.type: str = modal_type
        self.accuracy: float = accuracy
        self.url: str = url
        self.isActive: bool = isActive
        self.version: str = version
        self.created_date: datetime = datetime.utcnow()
        self.updated_date: datetime = datetime.utcnow()
        self.modal_id: Any = None  # Will be set after saving to the database

    def save(self) -> Any:
        result = mongo.db.modal.insert_one(self.to_dict())
        self.modal_id = result.inserted_id
        return result

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "accuracy": self.accuracy,
            "url": self.url,
            "isActive": self.isActive,
            "version": self.version,
            "createdDate": self.created_date,
            "updatedDate": self.updated_date
        }


class AudioFiles:
    def __init__(self, user_id, url, isPredicted, activitySessionId, text):
        self.user_id = user_id
        self.url = url
        self.isPredicted = isPredicted
        self.activitySessionId = activitySessionId
        self.text = text
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
            "isPredicted": self.isPredicted,
            "activitySessionId": self.activitySessionId,
            "text": self.text,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class Classifications:
    def __init__(self, title):
        self.title = title
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.classification_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "title": self.title,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class Predictions:
    def __init__(self, user_id, audioFileId, modalId, totalFiles, fluency, disfluency, naturalPause, interjection, noSpeech, music, activitySessionId):
        self.user_id = user_id
        self.audioFileId = audioFileId
        self.modalId = modalId
        self.totalFiles = totalFiles
        self.fluency = fluency
        self.disfluency = disfluency
        self.naturalPause = naturalPause
        self.interjection = interjection
        self.noSpeech = noSpeech
        self.music = music
        self.activitySessionId = activitySessionId
        self.createdDate = datetime.utcnow()
        self.updatedDate = datetime.utcnow()

    def save(self):
        result = mongo.db.predictions.insert_one(self.to_dict())
        self.predictions_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "audioFileId": self.audioFileId,
            "modalId": self.modalId,
            "totalFiles": self.totalFiles,
            "fluency": self.fluency,
            "disfluency": self.disfluency,
            "naturalPause": self.naturalPause,
            "interjection": self.interjection,
            "noSpeech": self.noSpeech,
            "music": self.music,
            "activitySessionId": self.activitySessionId,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class Feedback:
    def __init__(self, user_id, predictionId, feedback, disfluency, fluency, interjection, naturalPause, activitySessionId):
        self.user_id = user_id
        self.predictionId = predictionId
        self.feedback = feedback
        self.disfluency = disfluency
        self.fluency = fluency
        self.interjection = interjection
        self.naturalPause = naturalPause
        self.activitySessionId = activitySessionId
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.feedback_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "predictionId": self.predictionId,
            "feedback": self.feedback,
            "disfluency": self.disfluency,
            "fluency": self.fluency,
            "interjection": self.interjection,
            "naturalPause": self.naturalPause,
            "activitySessionId": self.activitySessionId,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class Activity:
    def __init__(self, title, endpoint):
        self.title = title
        self.endpoint = endpoint
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.activity_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "title": self.title,
            "endpoint": self.endpoint,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class ActivitySession:
    def __init__(self, user_id, activity_id, theme_id):
        self.user_id = user_id
        self.activity_id = activity_id
        self.theme_id = theme_id
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.activitySession_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "activity_id": self.activity_id,
            "theme_id":  self.theme_id,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class ActivityTheme:
    def __init__(self, theme, activity_id):
        self.theme = theme

        self.activity_id = activity_id

        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.activityTheme_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "theme": self.theme,
            "activity_id": self.activity_id,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }


class Dialogue:
    def __init__(self, theme_id,  user_id, activity_id, feedback, friend_name):
        self.theme_id = theme_id
        self.user_id = user_id
        self.activity_id = activity_id
        self.feedback = feedback
        self.friend_name = friend_name
        self.created_date = datetime.utcnow()
        self.updated_date = datetime.utcnow()

    def save(self):
        result = mongo.db.modal.insert_one(self.to_dict())
        self.activityDialogue_id = result.inserted_id
        return result

    def to_dict(self):
        return {
            "theme_id": self.theme_id,
            "user_id": self.user_id,
            "activity_id": self.activity_id,
            "feedback": self.feedback,
            "friend_name": self.friend_name,
            "createdDate": self.createdDate,
            "updatedDate": self.updatedDate
        }
